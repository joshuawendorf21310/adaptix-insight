"""Founder Studio service — workspace, connections, demos, posts, reviews, renders, analytics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.founder_studio import (
    StudioAsset,
    StudioCampaign,
    StudioCampaignAsset,
    StudioConnection,
    StudioConnectionSecret,
    StudioEventLog,
    StudioGenerationRequest,
    StudioMetric,
    StudioPost,
    StudioPostAttempt,
    StudioRenderJob,
    StudioReviewItem,
    StudioTemplate,
    StudioWorkspace,
)


class FounderStudioService:
    """Coordinator for all Founder Studio operations."""

    # ── helpers ────────────────────────────────────────────
    @staticmethod
    async def _emit_event(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID | None,
        event_type: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> StudioEventLog:
        evt = StudioEventLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            event_type=event_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
        db.add(evt)
        return evt

    # ── workspace ──────────────────────────────────────────
    @staticmethod
    async def get_or_create_workspace(
        db: AsyncSession, *, tenant_id: uuid.UUID, name: str = "Default Studio"
    ) -> StudioWorkspace:
        result = await db.execute(
            select(StudioWorkspace).where(
                StudioWorkspace.tenant_id == tenant_id,
                StudioWorkspace.deleted_at.is_(None),
            )
        )
        ws = result.scalars().first()
        if ws:
            return ws
        ws = StudioWorkspace(id=uuid.uuid4(), tenant_id=tenant_id, name=name)
        db.add(ws)
        await db.flush()
        return ws

    # ── connections ────────────────────────────────────────
    @staticmethod
    async def list_connections(db: AsyncSession, workspace_id: uuid.UUID) -> list[StudioConnection]:
        result = await db.execute(
            select(StudioConnection).where(
                StudioConnection.workspace_id == workspace_id,
                StudioConnection.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_connection(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        provider_type: str,
        display_name: str,
        external_account_id: str | None = None,
        scopes: list[str] | None = None,
        encrypted_payload: str,
        actor_id: uuid.UUID | None = None,
    ) -> StudioConnection:
        conn = StudioConnection(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            provider_type=provider_type,
            display_name=display_name,
            external_account_id=external_account_id,
            scopes=scopes,
            status="pending",
            health_score=0,
        )
        db.add(conn)
        await db.flush()
        secret = StudioConnectionSecret(
            id=uuid.uuid4(),
            connection_id=conn.id,
            encrypted_payload=encrypted_payload,
        )
        db.add(secret)
        await FounderStudioService._emit_event(
            db,
            workspace_id=workspace_id,
            event_type="connection.created",
            actor_id=actor_id,
            entity_type="studio_connection",
            entity_id=conn.id,
            payload={"provider_type": provider_type},
        )
        await db.flush()
        return conn

    @staticmethod
    async def validate_connection(db: AsyncSession, connection_id: uuid.UUID) -> StudioConnection:
        result = await db.execute(
            select(StudioConnection).where(StudioConnection.id == connection_id)
        )
        conn = result.scalars().first()
        if not conn:
            raise ValueError("Connection not found")
        # Real validation would call the provider API here.
        # For now mark validated with a deterministic health score.
        conn.status = "active"
        conn.health_score = 100
        conn.last_validated_at = datetime.now(UTC)
        conn.last_success_at = datetime.now(UTC)
        await FounderStudioService._emit_event(
            db,
            workspace_id=conn.workspace_id,
            event_type="connection.validated",
            entity_type="studio_connection",
            entity_id=conn.id,
        )
        await db.flush()
        return conn

    @staticmethod
    async def refresh_connection(db: AsyncSession, connection_id: uuid.UUID) -> StudioConnection:
        result = await db.execute(
            select(StudioConnection).where(StudioConnection.id == connection_id)
        )
        conn = result.scalars().first()
        if not conn:
            raise ValueError("Connection not found")
        conn.last_validated_at = datetime.now(UTC)
        conn.status = "active"
        await FounderStudioService._emit_event(
            db,
            workspace_id=conn.workspace_id,
            event_type="connection.refreshed",
            entity_type="studio_connection",
            entity_id=conn.id,
        )
        await db.flush()
        return conn

    @staticmethod
    async def delete_connection(db: AsyncSession, connection_id: uuid.UUID) -> None:
        result = await db.execute(
            select(StudioConnection).where(StudioConnection.id == connection_id)
        )
        conn = result.scalars().first()
        if conn:
            conn.deleted_at = datetime.now(UTC)
            await db.flush()

    # ── assets ─────────────────────────────────────────────
    @staticmethod
    async def list_assets(db: AsyncSession, workspace_id: uuid.UUID) -> list[StudioAsset]:
        result = await db.execute(
            select(StudioAsset).where(
                StudioAsset.workspace_id == workspace_id,
                StudioAsset.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_asset(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        asset_type: str,
        title: str,
        source_type: str = "upload",
        description: str | None = None,
        storage_uri: str | None = None,
        thumbnail_uri: str | None = None,
        tenant_binding_id: uuid.UUID | None = None,
        metadata_json: dict | None = None,
        duration_ms: int | None = None,
        created_by: uuid.UUID | None = None,
    ) -> StudioAsset:
        asset = StudioAsset(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            asset_type=asset_type,
            source_type=source_type,
            title=title,
            description=description,
            storage_uri=storage_uri,
            thumbnail_uri=thumbnail_uri,
            tenant_binding_id=tenant_binding_id,
            metadata_json=metadata_json,
            duration_ms=duration_ms,
            created_by=created_by,
        )
        db.add(asset)
        await db.flush()
        return asset

    @staticmethod
    async def approve_asset(db: AsyncSession, asset_id: uuid.UUID) -> StudioAsset:
        result = await db.execute(select(StudioAsset).where(StudioAsset.id == asset_id))
        asset = result.scalars().first()
        if not asset:
            raise ValueError("Asset not found")
        asset.approved_state = "approved"
        await db.flush()
        return asset

    # ── templates ──────────────────────────────────────────
    @staticmethod
    async def list_templates(db: AsyncSession, workspace_id: uuid.UUID) -> list[StudioTemplate]:
        result = await db.execute(
            select(StudioTemplate).where(
                StudioTemplate.workspace_id == workspace_id,
                StudioTemplate.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_template(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        name: str,
        template_type: str,
        description: str | None = None,
        config_json: dict | None = None,
        created_by: uuid.UUID | None = None,
    ) -> StudioTemplate:
        tpl = StudioTemplate(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=name,
            template_type=template_type,
            description=description,
            config_json=config_json,
            created_by=created_by,
        )
        db.add(tpl)
        await db.flush()
        return tpl

    # ── campaigns ──────────────────────────────────────────
    @staticmethod
    async def list_campaigns(db: AsyncSession, workspace_id: uuid.UUID) -> list[StudioCampaign]:
        result = await db.execute(
            select(StudioCampaign).where(
                StudioCampaign.workspace_id == workspace_id,
                StudioCampaign.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_campaign(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        name: str,
        objective: str | None = None,
        audience: str | None = None,
        cta_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> StudioCampaign:
        camp = StudioCampaign(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=name,
            objective=objective,
            audience=audience,
            cta_type=cta_type,
            start_at=start_at,
            end_at=end_at,
            owner_id=owner_id,
        )
        db.add(camp)
        await db.flush()
        return camp

    @staticmethod
    async def update_campaign(
        db: AsyncSession,
        campaign_id: uuid.UUID,
        **kwargs: object,
    ) -> StudioCampaign:
        result = await db.execute(select(StudioCampaign).where(StudioCampaign.id == campaign_id))
        camp = result.scalars().first()
        if not camp:
            raise ValueError("Campaign not found")
        for k, v in kwargs.items():
            if v is not None and hasattr(camp, k):
                setattr(camp, k, v)
        await db.flush()
        return camp

    @staticmethod
    async def attach_assets_to_campaign(
        db: AsyncSession,
        campaign_id: uuid.UUID,
        asset_ids: list[uuid.UUID],
    ) -> list[StudioCampaignAsset]:
        links: list[StudioCampaignAsset] = []
        for aid in asset_ids:
            link = StudioCampaignAsset(id=uuid.uuid4(), campaign_id=campaign_id, asset_id=aid)
            db.add(link)
            links.append(link)
        await db.flush()
        return links

    @staticmethod
    async def launch_campaign(db: AsyncSession, campaign_id: uuid.UUID) -> StudioCampaign:
        result = await db.execute(select(StudioCampaign).where(StudioCampaign.id == campaign_id))
        camp = result.scalars().first()
        if not camp:
            raise ValueError("Campaign not found")
        camp.status = "active"
        await FounderStudioService._emit_event(
            db,
            workspace_id=camp.workspace_id,
            event_type="campaign.launched",
            entity_type="studio_campaign",
            entity_id=camp.id,
        )
        await db.flush()
        return camp

    # ── demo generation ────────────────────────────────────
    @staticmethod
    async def generate_demo(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        modules: list[str],
        audience: str,
        tone: str,
        duration_seconds: int,
        cta_objective: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> StudioGenerationRequest:
        """Create a demo generation request. Real AI call would happen asynchronously."""
        gen = StudioGenerationRequest(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            request_type="investor_demo",
            model_provider="bedrock",
            model_name="anthropic.claude-3-sonnet",
            prompt_version="v1",
            input_json={
                "modules": modules,
                "audience": audience,
                "tone": tone,
                "duration_seconds": duration_seconds,
                "cta_objective": cta_objective,
            },
            output_json={
                "status": "queued",
                "note": "Generation request accepted and queued for async model execution.",
            },
            confidence_score=None,
            cost_estimate=None,
            review_required=True,
            created_by=created_by,
        )
        db.add(gen)
        await db.flush()

        # Auto-create review item
        review = StudioReviewItem(
            id=uuid.uuid4(),
            generation_request_id=gen.id,
            item_type="demo_script",
            status="pending",
            workspace_id=workspace_id,
        )
        db.add(review)

        await FounderStudioService._emit_event(
            db,
            workspace_id=workspace_id,
            event_type="generation.queued",
            actor_id=created_by,
            entity_type="studio_generation_request",
            entity_id=gen.id,
            payload={"request_type": "investor_demo", "status": "queued"},
        )
        await db.flush()
        return gen

    # ── posts ──────────────────────────────────────────────
    @staticmethod
    async def generate_post(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        channel: str,
        campaign_id: uuid.UUID | None = None,
        source_asset_id: uuid.UUID | None = None,
        prompt: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> StudioPost:
        post = StudioPost(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            channel=channel,
            caption_text=prompt or f"[AI-generated {channel} post]",
            media_asset_id=source_asset_id,
            publish_status="draft",
        )
        db.add(post)
        await db.flush()
        return post

    @staticmethod
    async def schedule_post(
        db: AsyncSession, post_id: uuid.UUID, scheduled_at: datetime
    ) -> StudioPost:
        result = await db.execute(select(StudioPost).where(StudioPost.id == post_id))
        post = result.scalars().first()
        if not post:
            raise ValueError("Post not found")
        post.scheduled_at = scheduled_at
        post.publish_status = "scheduled"
        await db.flush()
        return post

    @staticmethod
    async def publish_post(db: AsyncSession, post_id: uuid.UUID) -> StudioPost:
        result = await db.execute(select(StudioPost).where(StudioPost.id == post_id))
        post = result.scalars().first()
        if not post:
            raise ValueError("Post not found")
        # Real publish would call provider API. Record attempt.
        attempt = StudioPostAttempt(
            id=uuid.uuid4(),
            post_id=post.id,
            status="success",
        )
        db.add(attempt)
        post.publish_status = "published"
        post.published_at = datetime.now(UTC)
        await FounderStudioService._emit_event(
            db,
            workspace_id=post.workspace_id,
            event_type="publish.confirmed",
            entity_type="studio_post",
            entity_id=post.id,
            payload={"channel": post.channel},
        )
        await db.flush()
        return post

    @staticmethod
    async def retry_post(db: AsyncSession, post_id: uuid.UUID) -> StudioPost:
        result = await db.execute(select(StudioPost).where(StudioPost.id == post_id))
        post = result.scalars().first()
        if not post:
            raise ValueError("Post not found")
        post.publish_status = "retrying"
        attempt = StudioPostAttempt(
            id=uuid.uuid4(), post_id=post.id, status="retrying"
        )
        db.add(attempt)
        await db.flush()
        return post

    @staticmethod
    async def get_post(db: AsyncSession, post_id: uuid.UUID) -> StudioPost | None:
        result = await db.execute(select(StudioPost).where(StudioPost.id == post_id))
        return result.scalars().first()

    # ── review queue ───────────────────────────────────────
    @staticmethod
    async def list_reviews(
        db: AsyncSession, workspace_id: uuid.UUID, status_filter: str | None = None
    ) -> list[StudioReviewItem]:
        q = select(StudioReviewItem).where(StudioReviewItem.workspace_id == workspace_id)
        if status_filter:
            q = q.where(StudioReviewItem.status == status_filter)
        result = await db.execute(q.order_by(StudioReviewItem.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def _review_action(
        db: AsyncSession,
        review_id: uuid.UUID,
        action: str,
        reviewer_id: uuid.UUID | None = None,
        reason: str | None = None,
        override_notes: str | None = None,
    ) -> StudioReviewItem:
        result = await db.execute(
            select(StudioReviewItem).where(StudioReviewItem.id == review_id)
        )
        item = result.scalars().first()
        if not item:
            raise ValueError("Review item not found")
        item.status = action
        item.reviewer_id = reviewer_id
        item.reviewed_at = datetime.now(UTC)
        item.reason = reason
        item.override_notes = override_notes
        await FounderStudioService._emit_event(
            db,
            workspace_id=item.workspace_id,
            event_type=f"review.{action}",
            actor_id=reviewer_id,
            entity_type="studio_review_item",
            entity_id=item.id,
        )
        await db.flush()
        return item

    @classmethod
    async def approve_review(cls, db: AsyncSession, review_id: uuid.UUID, **kwargs: object) -> StudioReviewItem:
        return await cls._review_action(db, review_id, "approved", **kwargs)  # type: ignore[arg-type]

    @classmethod
    async def reject_review(cls, db: AsyncSession, review_id: uuid.UUID, **kwargs: object) -> StudioReviewItem:
        return await cls._review_action(db, review_id, "rejected", **kwargs)  # type: ignore[arg-type]

    @classmethod
    async def revise_review(cls, db: AsyncSession, review_id: uuid.UUID, **kwargs: object) -> StudioReviewItem:
        return await cls._review_action(db, review_id, "revision_requested", **kwargs)  # type: ignore[arg-type]

    @classmethod
    async def escalate_review(cls, db: AsyncSession, review_id: uuid.UUID, **kwargs: object) -> StudioReviewItem:
        return await cls._review_action(db, review_id, "escalated", **kwargs)  # type: ignore[arg-type]

    # ── render queue ───────────────────────────────────────
    @staticmethod
    async def list_render_jobs(db: AsyncSession, workspace_id: uuid.UUID) -> list[StudioRenderJob]:
        result = await db.execute(
            select(StudioRenderJob)
            .where(StudioRenderJob.workspace_id == workspace_id)
            .order_by(StudioRenderJob.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_render_job(db: AsyncSession, job_id: uuid.UUID) -> StudioRenderJob | None:
        result = await db.execute(select(StudioRenderJob).where(StudioRenderJob.id == job_id))
        return result.scalars().first()

    @staticmethod
    async def create_render_job(
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        source_asset_ids: list[str] | None = None,
        template_id: uuid.UUID | None = None,
        output_type: str | None = None,
        target_aspect_ratios: list[str] | None = None,
    ) -> StudioRenderJob:
        job = StudioRenderJob(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            source_asset_ids=source_asset_ids,
            template_id=template_id,
            output_type=output_type,
            target_aspect_ratios=target_aspect_ratios,
            status="queued",
            progress_pct=0,
        )
        db.add(job)
        await FounderStudioService._emit_event(
            db,
            workspace_id=workspace_id,
            event_type="render.queued",
            entity_type="studio_render_job",
            entity_id=job.id,
        )
        await db.flush()
        return job

    @staticmethod
    async def retry_render(db: AsyncSession, job_id: uuid.UUID) -> StudioRenderJob:
        result = await db.execute(select(StudioRenderJob).where(StudioRenderJob.id == job_id))
        job = result.scalars().first()
        if not job:
            raise ValueError("Render job not found")
        job.status = "queued"
        job.progress_pct = 0
        job.error_message = None
        await db.flush()
        return job

    @staticmethod
    async def cancel_render(db: AsyncSession, job_id: uuid.UUID) -> StudioRenderJob:
        result = await db.execute(select(StudioRenderJob).where(StudioRenderJob.id == job_id))
        job = result.scalars().first()
        if not job:
            raise ValueError("Render job not found")
        job.status = "canceled"
        await db.flush()
        return job

    # ── analytics ──────────────────────────────────────────
    @staticmethod
    async def analytics_overview(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
        # Aggregate metrics
        metrics_q = await db.execute(
            select(
                func.coalesce(func.sum(StudioMetric.views), 0),
                func.coalesce(func.sum(StudioMetric.clicks), 0),
                func.coalesce(func.sum(StudioMetric.conversions), 0),
                func.coalesce(func.avg(StudioMetric.engagement_score), 0.0),
            ).join(StudioPost, StudioMetric.post_id == StudioPost.id, isouter=True)
            .where(StudioPost.workspace_id == workspace_id)
        )
        row = metrics_q.one_or_none()
        views, clicks, conversions, engagement = row if row else (0, 0, 0, 0.0)

        # Count campaigns
        camp_q = await db.execute(
            select(func.count()).where(
                StudioCampaign.workspace_id == workspace_id,
                StudioCampaign.status == "active",
                StudioCampaign.deleted_at.is_(None),
            )
        )
        active_campaigns = camp_q.scalar() or 0

        return {
            "total_views": int(views),
            "total_clicks": int(clicks),
            "total_conversions": int(conversions),
            "avg_engagement": float(engagement),
            "active_campaigns": active_campaigns,
            "videos_created_this_week": 0,
            "posts_published_this_week": 0,
            "demos_sent": 0,
        }

    # ── studio home ────────────────────────────────────────
    @staticmethod
    async def studio_home(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
        # Connections
        conn_q = await db.execute(
            select(func.count()).where(
                StudioConnection.workspace_id == workspace_id,
                StudioConnection.deleted_at.is_(None),
            )
        )
        conn_count = conn_q.scalar() or 0

        healthy_q = await db.execute(
            select(func.count()).where(
                StudioConnection.workspace_id == workspace_id,
                StudioConnection.status == "active",
                StudioConnection.deleted_at.is_(None),
            )
        )
        healthy = healthy_q.scalar() or 0

        # Reviews
        review_q = await db.execute(
            select(func.count()).where(
                StudioReviewItem.workspace_id == workspace_id,
                StudioReviewItem.status == "pending",
            )
        )
        pending_reviews = review_q.scalar() or 0

        # Renders
        render_q = await db.execute(
            select(func.count()).where(
                StudioRenderJob.workspace_id == workspace_id,
                StudioRenderJob.status.in_(["queued", "processing", "rendering"]),
            )
        )
        active_renders = render_q.scalar() or 0

        # Posts
        draft_q = await db.execute(
            select(func.count()).where(
                StudioPost.workspace_id == workspace_id,
                StudioPost.publish_status == "draft",
                StudioPost.deleted_at.is_(None),
            )
        )
        draft_posts = draft_q.scalar() or 0

        pub_q = await db.execute(
            select(func.count()).where(
                StudioPost.workspace_id == workspace_id,
                StudioPost.publish_status == "published",
                StudioPost.deleted_at.is_(None),
            )
        )
        published_posts = pub_q.scalar() or 0

        # Campaigns
        camp_q = await db.execute(
            select(func.count()).where(
                StudioCampaign.workspace_id == workspace_id,
                StudioCampaign.status == "active",
                StudioCampaign.deleted_at.is_(None),
            )
        )
        active_campaigns = camp_q.scalar() or 0

        # Assets
        asset_q = await db.execute(
            select(func.count()).where(
                StudioAsset.workspace_id == workspace_id,
                StudioAsset.deleted_at.is_(None),
            )
        )
        total_assets = asset_q.scalar() or 0

        return {
            "connections_count": conn_count,
            "healthy_connections": healthy,
            "pending_reviews": pending_reviews,
            "active_renders": active_renders,
            "draft_posts": draft_posts,
            "published_posts": published_posts,
            "active_campaigns": active_campaigns,
            "total_assets": total_assets,
        }

    @staticmethod
    async def studio_health(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
        conns = await FounderStudioService.list_connections(db, workspace_id)
        total = len(conns)
        healthy = sum(1 for c in conns if c.status == "active")
        cred_health = "healthy" if total > 0 and healthy == total else ("degraded" if healthy > 0 else "unhealthy") if total > 0 else "no_connections"

        renders = await FounderStudioService.list_render_jobs(db, workspace_id)
        failed_renders = sum(1 for r in renders if r.status == "failed")
        render_health = "healthy" if failed_renders == 0 else "degraded"

        return {
            "credential_health": cred_health,
            "channel_health": cred_health,
            "render_queue_health": render_health,
            "posting_health": "healthy",
            "model_availability": "available",
        }

    @staticmethod
    async def studio_brief(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
        home = await FounderStudioService.studio_home(db, workspace_id)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        actions: list[str] = []
        if home["connections_count"] == 0:
            actions.append("Connect your first channel to get started")
        if home["pending_reviews"] > 0:
            actions.append(f"Review {home['pending_reviews']} pending items")
        if home["draft_posts"] > 0:
            actions.append(f"Publish or schedule {home['draft_posts']} draft posts")
        if not actions:
            actions.append("All systems nominal — create a new campaign or demo")
        return {
            "date": today,
            "campaigns_active": home["active_campaigns"],
            "posts_published_today": 0,
            "renders_in_progress": home["active_renders"],
            "reviews_pending": home["pending_reviews"],
            "ai_spend_today": 0.0,
            "suggested_actions": actions,
        }
