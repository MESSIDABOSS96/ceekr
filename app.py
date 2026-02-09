"""Twitter Account Finder - Streamlit UI."""

import asyncio
from typing import Optional

import streamlit as st

from config import INITIAL_RESULTS, LOAD_MORE_BATCH, validate_config
from core.llm import LLMClient
from core.models import RankedAccount, TwitterAccount
from core.twitter import SearchOrchestrator, TwitterClient


# Page config
st.set_page_config(
    page_title="Twitter Account Finder",
    page_icon="🔍",
    layout="centered",
)

# Custom CSS for cards
st.markdown(
    """
<style>
.account-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    background-color: #fafafa;
}
.account-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.account-handle {
    font-weight: bold;
    font-size: 1.1em;
}
.account-score {
    background-color: #4CAF50;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
}
.account-meta {
    color: #666;
    font-size: 0.9em;
    margin-bottom: 8px;
}
.network-badge {
    background-color: #2196F3;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.8em;
    margin-left: 8px;
}
.why-relevant {
    background-color: #fff3cd;
    padding: 8px;
    border-radius: 4px;
    margin-top: 8px;
    font-size: 0.9em;
}
</style>
""",
    unsafe_allow_html=True,
)


def init_session_state():
    """Initialize session state variables."""
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "all_ranked" not in st.session_state:
        st.session_state.all_ranked = []
    if "shown_count" not in st.session_state:
        st.session_state.shown_count = INITIAL_RESULTS
    if "search_status" not in st.session_state:
        st.session_state.search_status = None
    if "clarification_needed" not in st.session_state:
        st.session_state.clarification_needed = None
    if "last_who" not in st.session_state:
        st.session_state.last_who = ""
    if "last_why" not in st.session_state:
        st.session_state.last_why = ""


def render_account_card(ranked: RankedAccount):
    """Render a single account card."""
    acc = ranked.account

    # Network badge
    network_badge = ""
    if acc.network.follows_you and acc.network.you_follow:
        network_badge = '<span class="network-badge">Mutuals</span>'
    elif acc.network.follows_you:
        network_badge = '<span class="network-badge">Follows you</span>'
    elif acc.network.you_follow:
        network_badge = '<span class="network-badge">You follow</span>'

    # Follower count formatting
    followers = acc.followers_count
    if followers >= 1_000_000:
        followers_str = f"{followers / 1_000_000:.1f}M"
    elif followers >= 1_000:
        followers_str = f"{followers / 1_000:.1f}K"
    else:
        followers_str = str(followers)

    # Score color
    score = ranked.relevance_score
    if score >= 8:
        score_color = "#4CAF50"  # Green
    elif score >= 6:
        score_color = "#FF9800"  # Orange
    else:
        score_color = "#9E9E9E"  # Gray

    st.markdown(
        f"""
<div class="account-card">
    <div class="account-header">
        <span class="account-handle">@{acc.handle} ({acc.name}){network_badge}</span>
        <span class="account-score" style="background-color: {score_color};">{score:.1f}</span>
    </div>
    <div class="account-meta">{followers_str} followers</div>
    <div>{acc.bio or 'No bio'}</div>
    <div class="why-relevant"><strong>WHY:</strong> {ranked.why_relevant}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # View profile button
    st.link_button("View Profile", acc.profile_url, use_container_width=False)
    st.divider()


async def run_search(who: str, why: Optional[str], status_placeholder) -> list[RankedAccount]:
    """Execute the full search pipeline."""
    llm = LLMClient()

    # Step 1: Check clarity
    status_placeholder.markdown("🔍 **Analyzing your request...**")
    clarity = llm.check_input_clarity(who, why)

    if not clarity.is_clear:
        st.session_state.clarification_needed = clarity.questions
        return []

    # Step 2: Generate queries
    status_placeholder.markdown("🔍 **Generating search strategies...**")
    queries_response = llm.generate_search_queries(who, why)

    if not queries_response.queries:
        st.error("Failed to generate search queries. Please try again.")
        return []

    # Step 3: Execute searches
    twitter = TwitterClient()
    await twitter.initialize()
    orchestrator = SearchOrchestrator(twitter)

    async def update_status(msg: str):
        status_placeholder.markdown(f"🔍 **{msg}**")

    query_strings = [q.query for q in queries_response.queries]

    # Show queries being used
    with st.expander("Search queries being used", expanded=False):
        for q in queries_response.queries:
            st.markdown(f"- `{q.query}` - _{q.angle}_")

    accounts = await orchestrator.execute_searches(query_strings, update_status)

    if not accounts:
        st.warning("No accounts found. Try broadening your search criteria.")
        return []

    # Step 4: Rank accounts
    status_placeholder.markdown(
        f"🔍 **Found {len(accounts)} accounts, analyzing relevance...**"
    )
    ranking = llm.rank_accounts(who, why, accounts)

    status_placeholder.markdown(
        f"✅ **Done! Found {len(ranking.ranked_accounts)} relevant accounts**"
    )

    return ranking.ranked_accounts


def main():
    """Main app entry point."""
    init_session_state()

    st.title("🔍 Twitter Account Finder")
    st.markdown(
        "Find relevant Twitter accounts for networking, research, or validation. "
        "Describe who you want to find and why."
    )

    # Check configuration
    config_errors = validate_config()
    if config_errors:
        st.error("Configuration issues:")
        for error in config_errors:
            st.markdown(f"- {error}")

        with st.expander("Setup Instructions"):
            st.markdown(
                """
### 1. Set up your Anthropic API key
1. Copy `.env.example` to `.env`
2. Add your Anthropic API key

### 2. Export Twitter cookies
1. Install browser extension: "Get cookies.txt LOCALLY"
2. Go to twitter.com while logged in
3. Export cookies to `cookies.txt` in project root
"""
            )
        return

    # Input form
    with st.form("search_form"):
        who = st.text_area(
            "Who are you looking for?",
            placeholder="e.g., Founders who have discussed user research challenges or customer discovery",
            help="Type of person + what they should have talked about",
            value=st.session_state.last_who,
        )

        why = st.text_area(
            "Why? (optional but helpful)",
            placeholder="e.g., I'm building an AI interview tool and want to validate the idea",
            help="Context helps find more relevant people",
            value=st.session_state.last_why,
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("Find Accounts", type="primary")
        with col2:
            small_accounts = st.checkbox("Prefer smaller accounts (<50K followers)")

    # Handle clarification
    if st.session_state.clarification_needed:
        st.warning("I need a bit more information to find the right people:")
        for q in st.session_state.clarification_needed:
            st.markdown(f"**{q.question}**")
            st.caption(f"_({q.reason})_")

        clarification = st.text_area("Your response:")
        if st.button("Continue with this clarification"):
            # Append clarification to the who field
            st.session_state.last_who = f"{who}\n\nClarification: {clarification}"
            st.session_state.clarification_needed = None
            st.rerun()

    # Run search
    if submitted and who:
        st.session_state.last_who = who
        st.session_state.last_why = why
        st.session_state.clarification_needed = None
        st.session_state.shown_count = INITIAL_RESULTS

        status_placeholder = st.empty()

        with st.spinner("Searching..."):
            results = asyncio.run(run_search(who, why or None, status_placeholder))

        if results:
            # Filter by follower count if requested
            if small_accounts:
                results = [r for r in results if r.account.followers_count < 50_000]

            st.session_state.all_ranked = results
            st.session_state.search_results = results[: st.session_state.shown_count]

    # Display results
    if st.session_state.search_results:
        st.subheader(f"Found {len(st.session_state.all_ranked)} relevant accounts")

        for ranked in st.session_state.search_results:
            render_account_card(ranked)

        # Load more button
        if st.session_state.shown_count < len(st.session_state.all_ranked):
            if st.button("Load more"):
                st.session_state.shown_count += LOAD_MORE_BATCH
                st.session_state.search_results = st.session_state.all_ranked[
                    : st.session_state.shown_count
                ]
                st.rerun()

        # Feedback section
        st.divider()
        st.markdown("**Not finding what you need?**")

        feedback = st.text_input(
            "What should we adjust?",
            placeholder="e.g., smaller accounts, more recent activity, different focus area",
        )

        if st.button("Search again with feedback") and feedback:
            new_who = f"{st.session_state.last_who}\n\nFeedback: {feedback}"
            st.session_state.last_who = new_who
            st.session_state.search_results = None
            st.session_state.all_ranked = []
            st.rerun()


if __name__ == "__main__":
    main()
