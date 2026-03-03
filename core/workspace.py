"""Workspace orchestrator — runs search pipeline then clusters into journals."""

import asyncio
import json
import math
import random
from uuid import uuid4

from algorithms import get_algorithm
from core.database import WorkspaceDB
from core.llm import LLMClient
from core.models import RankedAccount, SearchIntent, WorkspaceStatus

# Index-based palette — journal i gets JOURNAL_PALETTE[i % len]
JOURNAL_PALETTE = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#f59e0b",
    "#10b981", "#ec4899", "#f97316", "#14b8a6",
]

# Canvas bounds
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 800


def compute_layout(journal_count: int) -> list[tuple[float, float]]:
    """
    Compute organic scattered positions for journals on a canvas.
    Returns list of (x, y) tuples.
    """
    if journal_count == 0:
        return []
    if journal_count == 1:
        return [(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)]

    positions = []
    cx, cy = CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2
    radius = min(CANVAS_WIDTH, CANVAS_HEIGHT) * 0.3
    angle_step = 2 * math.pi / journal_count

    for i in range(journal_count):
        angle = angle_step * i - math.pi / 2  # start from top
        jitter_r = random.uniform(-radius * 0.2, radius * 0.2)
        jitter_a = random.uniform(-0.15, 0.15)
        r = radius + jitter_r
        a = angle + jitter_a
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        x = max(80, min(CANVAS_WIDTH - 80, x))
        y = max(80, min(CANVAS_HEIGHT - 80, y))
        positions.append((round(x, 1), round(y, 1)))

    return positions


def _serialize_account(ranked: RankedAccount) -> dict:
    """Serialize a RankedAccount to the same JSON shape the frontend consumes."""
    acc = ranked.account
    result = {
        "user_id": acc.user_id,
        "handle": acc.handle,
        "name": acc.name,
        "bio": acc.bio,
        "followers_count": acc.followers_count,
        "following_count": acc.following_count,
        "tweet_count": acc.tweet_count,
        "profile_url": acc.profile_url,
        "profile_image_url": acc.profile_image_url,
        "recent_tweets": [
            {
                "id": t.id,
                "text": t.text,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "like_count": t.like_count,
                "retweet_count": t.retweet_count,
                "reply_count": t.reply_count,
                "media_urls": t.media_urls,
            }
            for t in acc.recent_tweets
        ],
        "matched_queries": acc.matched_queries,
        "location": acc.location,
        "verified": acc.verified,
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
        "network": {
            "you_follow": acc.network.you_follow,
            "follows_you": acc.network.follows_you,
            "mutual_followers": acc.network.mutual_followers,
        },
        "why_relevant": ranked.why_relevant,
        "bucket": ranked.bucket,
        "summary": ranked.summary,
        "highlight_tweet_indices": ranked.highlight_tweet_indices,
        "suggested_approach": ranked.suggested_approach,
        "evidence_highlights": ranked.evidence_highlights,
        "confidence": ranked.confidence,
        "enrichment": None,
    }
    if ranked.enrichment:
        result["enrichment"] = {
            "external_link": ranked.enrichment.external_link,
            "link_label": ranked.enrichment.link_label,
            "context_note": ranked.enrichment.context_note,
        }
    return result


def _reconstruct_ranked_accounts(people_data: list[dict]) -> list[RankedAccount]:
    """Reconstruct RankedAccount objects from stored JSON for re-grouping."""
    from core.models import TwitterAccount, Tweet, NetworkInfo, EnrichmentData

    results = []
    for p in people_data:
        tweets = []
        for t in p.get("recent_tweets", []):
            tweets.append(Tweet(
                id=t.get("id", ""),
                text=t.get("text", ""),
                created_at=t.get("created_at"),
                like_count=t.get("like_count", 0),
                retweet_count=t.get("retweet_count", 0),
                reply_count=t.get("reply_count", 0),
                media_urls=t.get("media_urls", []),
            ))
        net = p.get("network", {})
        account = TwitterAccount(
            user_id=p["user_id"],
            handle=p["handle"],
            name=p.get("name", ""),
            bio=p.get("bio"),
            followers_count=p.get("followers_count", 0),
            following_count=p.get("following_count", 0),
            tweet_count=p.get("tweet_count", 0),
            profile_url=p.get("profile_url", f"https://twitter.com/{p['handle']}"),
            profile_image_url=p.get("profile_image_url"),
            location=p.get("location"),
            verified=p.get("verified", False),
            created_at=p.get("created_at"),
            recent_tweets=tweets,
            matched_queries=p.get("matched_queries", []),
            network=NetworkInfo(
                you_follow=net.get("you_follow", False),
                follows_you=net.get("follows_you", False),
                mutual_followers=net.get("mutual_followers", []),
            ),
        )
        enrichment = None
        if p.get("enrichment"):
            enrichment = EnrichmentData(**p["enrichment"])
        results.append(RankedAccount(
            account=account,
            relevance_score=p.get("relevance_score", 5.0),
            bucket=p.get("bucket", "good_match"),
            summary=p.get("summary", ""),
            highlight_tweet_indices=p.get("highlight_tweet_indices", []),
            why_relevant=p.get("why_relevant", ""),
            suggested_approach=p.get("suggested_approach"),
            evidence_highlights=p.get("evidence_highlights", []),
            confidence=p.get("confidence", "medium"),
            enrichment=enrichment,
        ))
    return results


async def _store_journals(
    db: WorkspaceDB,
    workspace_id: str,
    raw_journals: list[dict],
    axis_id: str,
    handle_to_uid: dict[str, str],
    user_id_to_pk: dict[str, int],
) -> list[dict]:
    """Persist journals to DB and return serialized journal dicts."""
    positions = compute_layout(len(raw_journals))
    journal_dicts = []

    for i, rj in enumerate(raw_journals):
        jid = uuid4().hex[:12]
        color = JOURNAL_PALETTE[i % len(JOURNAL_PALETTE)]
        x, y = positions[i] if i < len(positions) else (CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)

        await db.create_journal(
            journal_id=jid,
            workspace_id=workspace_id,
            label=rj["label"],
            description=rj.get("description", ""),
            theme="",  # deprecated
            color=color,
            canvas_x=x,
            canvas_y=y,
            sort_order=i,
        )

        # Assign people to journal
        handles = [h.lower().lstrip("@") for h in rj.get("handles", [])]
        notes = rj.get("journal_notes", {})
        assignments = []
        for h in handles:
            uid = handle_to_uid.get(h)
            if uid:
                note = notes.get(h, notes.get(f"@{h}", ""))
                assignments.append({"user_id": uid, "journal_note": note})

        if assignments:
            await db.add_people_to_journal(jid, assignments, user_id_to_pk)

        journal_dicts.append({
            "id": jid,
            "label": rj["label"],
            "description": rj.get("description", ""),
            "color": color,
            "people_count": len(assignments),
            "canvas_x": x,
            "canvas_y": y,
        })

    return journal_dicts


class WorkspaceOrchestrator:
    """Creates a workspace by running the search pipeline then clustering into journals."""

    def __init__(self, db: WorkspaceDB):
        self.db = db

    async def create_workspace(
        self,
        query: str,
        twitter,
        queue: asyncio.Queue,
        user_network=None,
    ) -> dict:
        """
        Full workspace creation flow:
        1. Persist shell workspace
        2. Run algorithm pipeline
        3. Store ranked accounts
        4. Discover grouping axes
        5. Generate journals along recommended axis
        6. Compute layout, persist everything
        7. Return workspace payload
        """
        workspace_id = uuid4().hex[:12]
        await self.db.create_workspace(workspace_id, query)

        # Run existing algorithm pipeline (streams progress/intent/queries via queue)
        algorithm = get_algorithm()
        result = await algorithm.run(query, twitter, queue, user_network)

        if not result.ranked_accounts:
            await self.db.update_workspace(
                workspace_id,
                status=WorkspaceStatus.READY.value,
                quality="weak",
                summary="No results found.",
                refinement_questions_json=json.dumps(result.refinement_questions),
            )
            return {
                "workspace_id": workspace_id,
                "query": query,
                "status": "ready",
                "summary": "No results found.",
                "quality": "weak",
                "journals": [],
                "axes": [],
                "active_axis_id": None,
                "recommendation_reason": "",
                "total_people": 0,
                "refinement_questions": result.refinement_questions,
            }

        # Serialize and store all people
        serialized = [_serialize_account(ra) for ra in result.ranked_accounts]
        user_id_to_pk = await self.db.store_people_batch(workspace_id, serialized)

        handle_to_uid = {ra.account.handle.lower(): ra.account.user_id for ra in result.ranked_accounts}

        llm = LLMClient()

        # Reuse intent from algorithm (avoids redundant LLM call)
        await queue.put(json.dumps({"message": "Organizing results into groups...", "step": "grouping"}))
        intent = result.intent or SearchIntent(persona=query, topic=query, goal="find relevant people")

        # For high-specificity searches, only group top/strong matches
        accounts_for_grouping = result.ranked_accounts
        if intent.specificity >= 4:
            high_quality = [ra for ra in result.ranked_accounts if ra.bucket in ("top_match", "strong_match")]
            if high_quality:
                accounts_for_grouping = high_quality
                print(f"[grouping] Specificity {intent.specificity}: using {len(high_quality)}/{len(result.ranked_accounts)} top/strong matches for grouping")

        # Enforce mandatory_terms on grouping input for high-specificity searches
        if intent.specificity >= 4 and intent.mandatory_terms:
            terms_lower = [t.lower() for t in intent.mandatory_terms]
            before = len(accounts_for_grouping)
            filtered_for_grouping = []
            for ra in accounts_for_grouping:
                text = f"{ra.account.name} {ra.account.handle} {ra.account.bio or ''}"
                for t in ra.account.recent_tweets:
                    text += f" {t.text}"
                text = text.lower()
                if any(t in text for t in terms_lower):
                    filtered_for_grouping.append(ra)
            if filtered_for_grouping:
                accounts_for_grouping = filtered_for_grouping
                if before != len(accounts_for_grouping):
                    print(f"[grouping mandatory_enforce] {before} → {len(accounts_for_grouping)}")

        # Combined axis discovery + journal generation (single LLM call)
        await queue.put(json.dumps({"message": "Finding best grouping angles...", "step": "grouping"}))
        axes_raw, recommended_key, recommendation_reason, summary, raw_journals = (
            await llm.discover_and_generate_journals(intent, accounts_for_grouping)
        )

        # Build axis objects with IDs
        axes_with_ids = []
        recommended_axis_id = None
        for ax in axes_raw:
            ax_id = f"ax-{uuid4().hex[:8]}"
            axes_with_ids.append({
                "id": ax_id,
                "axis_key": ax["axis_key"],
                "axis_label": ax["axis_label"],
                "example_groups": ax.get("example_groups", []),
            })
            if ax["axis_key"] == recommended_key:
                recommended_axis_id = ax_id

        # Fallback: use first axis if recommended_key didn't match
        if not recommended_axis_id and axes_with_ids:
            recommended_axis_id = axes_with_ids[0]["id"]

        # Store axes
        await self.db.create_axes_batch(workspace_id, axes_with_ids)

        # Persist journals
        journal_dicts = await _store_journals(
            self.db, workspace_id, raw_journals, recommended_axis_id or "",
            handle_to_uid, user_id_to_pk,
        )

        # Store intent + update workspace
        intent_json = json.dumps({
            "persona": intent.persona,
            "topic": intent.topic,
            "goal": intent.goal,
            "specificity": intent.specificity,
        })

        await self.db.update_workspace(
            workspace_id,
            status=WorkspaceStatus.READY.value,
            intent_json=intent_json,
            summary=summary,
            quality=result.quality,
            refinement_questions_json=json.dumps(result.refinement_questions),
            active_axis_id=recommended_axis_id,
            recommendation_reason=recommendation_reason,
        )

        return {
            "workspace_id": workspace_id,
            "query": query,
            "status": "ready",
            "summary": summary,
            "quality": result.quality,
            "journals": journal_dicts,
            "axes": [
                {
                    "id": a["id"],
                    "axis_key": a["axis_key"],
                    "axis_label": a["axis_label"],
                    "example_groups": a["example_groups"],
                }
                for a in axes_with_ids
            ],
            "active_axis_id": recommended_axis_id,
            "recommendation_reason": recommendation_reason,
            "total_people": len(result.ranked_accounts),
            "refinement_questions": result.refinement_questions,
        }

    async def regroup_workspace(self, workspace_id: str, axis_id: str) -> dict:
        """
        Re-group an existing workspace along a different axis.
        People data is untouched — only journals are regenerated.
        """
        # Load workspace
        ws = await self.db.get_workspace(workspace_id)
        if not ws:
            raise ValueError("Workspace not found")

        # Load target axis
        axes = await self.db.get_axes(workspace_id)
        target_axis = next((a for a in axes if a["id"] == axis_id), None)
        if not target_axis:
            raise ValueError(f"Axis {axis_id} not found")

        # Reconstruct intent
        intent = SearchIntent(persona=ws["query"], topic=ws["query"], goal="find relevant people")
        if ws.get("intent_json"):
            intent_data = json.loads(ws["intent_json"])
            intent = SearchIntent(**intent_data)

        # Load all people and reconstruct RankedAccount objects
        people_data = await self.db.get_all_workspace_people(workspace_id)
        ranked_accounts = _reconstruct_ranked_accounts(people_data)

        if not ranked_accounts:
            raise ValueError("No people in workspace")

        handle_to_uid = {ra.account.handle.lower(): ra.account.user_id for ra in ranked_accounts}

        # Rebuild user_id_to_pk mapping
        cursor = await self.db._db.execute(
            "SELECT id, user_id FROM workspace_people WHERE workspace_id = ?",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        user_id_to_pk = {row["user_id"]: row["id"] for row in rows}

        # Generate journals with new axis
        llm = LLMClient()
        summary, raw_journals = await llm.generate_journals(
            intent, ranked_accounts,
            target_axis["axis_label"], target_axis.get("example_groups", []),
        )

        # Delete old journals
        await self.db.delete_journals_for_workspace(workspace_id)

        # Store new journals
        journal_dicts = await _store_journals(
            self.db, workspace_id, raw_journals, axis_id,
            handle_to_uid, user_id_to_pk,
        )

        # Update workspace active axis
        await self.db.update_workspace(
            workspace_id,
            active_axis_id=axis_id,
            summary=summary,
        )

        return {
            "active_axis_id": axis_id,
            "summary": summary,
            "journals": journal_dicts,
        }

    async def run_targeted_search(
        self,
        workspace_id: str,
        search_description: str,
    ) -> list[dict]:
        """
        Lightweight targeted search: generate 1-2 queries, search Twitter,
        dedupe against existing workspace people, rank, and merge results.

        Returns list of serialized new RankedAccount dicts.
        """
        from core.twitter import TwitterClient

        # Load existing workspace people to dedupe
        existing_people = await self.db.get_all_workspace_people(workspace_id)
        existing_handles = {p["handle"].lower() for p in existing_people}
        existing_user_ids = {p["user_id"] for p in existing_people}

        # Load workspace intent
        ws = await self.db.get_workspace(workspace_id)
        intent = SearchIntent(persona=ws["query"], topic=ws["query"], goal="find relevant people")
        if ws.get("intent_json"):
            import json
            intent_data = json.loads(ws["intent_json"])
            intent = SearchIntent(**intent_data)

        llm = LLMClient()
        twitter = TwitterClient()
        await twitter.initialize()

        # Step 1: Generate 1-2 targeted queries
        queries = await llm.generate_targeted_queries(
            search_description, list(existing_handles)[:20]
        )
        if not queries:
            return []

        # Step 2: Execute Twitter searches
        from config import TWEETS_PER_QUERY
        all_accounts = {}
        for sq in queries:
            try:
                accounts = await twitter.search_tweets(
                    sq.query, max_results=TWEETS_PER_QUERY, search_type="Top"
                )
                for acc in accounts:
                    # Dedupe against existing workspace + within this search
                    if acc.user_id not in existing_user_ids and acc.handle.lower() not in existing_handles:
                        if acc.user_id not in all_accounts:
                            all_accounts[acc.user_id] = acc
                            acc.matched_queries = [sq.query]
                        else:
                            all_accounts[acc.user_id].matched_queries.append(sq.query)
            except Exception as e:
                print(f"[targeted_search] Query failed: {sq.query}: {e}")

        if not all_accounts:
            return []

        accounts_list = list(all_accounts.values())

        # Step 3: Fast rank with Haiku (single batch, small set)
        ranking_response = await llm.rank_accounts(intent, accounts_list)
        new_ranked = ranking_response.ranked_accounts

        if not new_ranked:
            return []

        # Step 4: Store new people in workspace
        serialized = [_serialize_account(ra) for ra in new_ranked]
        await self.db.store_people_batch(workspace_id, serialized)

        return serialized
