import os
import json
import streamlit as st
from dotenv import load_dotenv

# Load .env BEFORE importing agents, so HTTP_PROXY and API keys are available
# when OpenAI clients are initialised.
load_dotenv()

from agents.requirement_parser import RequirementParser
from agents.redflag_detector import RedFlagDetector
from agents.comparison_generator import ComparisonGenerator
from agents.inquiry_drafter import InquiryDrafter
from utils import CostCalculator
from utils.filter_engine import filter_listings

st.set_page_config(
    page_title="London Rental Copilot",
    page_icon=":material/home:",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _data_file_hash():
    """Return a hash based on data file mtimes so cache auto-invalidates when JSON updates."""
    files = [
        "data/sample_listings.json",
        "data/borough_council_tax.json",
        "data/station_zone_map.json",
        "data/travelcard_costs.json",
    ]
    return tuple(os.path.getmtime(f) for f in files if os.path.exists(f))


# Load static data
@st.cache_data
def load_data(_hash):
    with open("data/sample_listings.json", "r", encoding="utf-8") as f:
        listings = json.load(f)
    with open("data/borough_council_tax.json", "r", encoding="utf-8") as f:
        council_tax = json.load(f)
    with open("data/station_zone_map.json", "r", encoding="utf-8") as f:
        stations = json.load(f)
    with open("data/travelcard_costs.json", "r", encoding="utf-8") as f:
        travelcards = json.load(f)
    return listings, council_tax, stations, travelcards


listings, council_tax, stations, _ = load_data(_hash=_data_file_hash())

# Sidebar
with st.sidebar:
    st.title("London Rental Copilot")
    st.markdown("AI-powered decision support for London renters.")
    st.divider()
    st.markdown("### Your Constraints")
    st.markdown("Enter your requirements in natural language below.")
    st.divider()
    st.markdown("**Note**: This is an MVP. Listings are sampled, not live.")

# Main content
st.header("Find Your Flat — The Smart Way")

# Tab layout for the four core features
tab_search, tab_flags, tab_compare, tab_email = st.tabs([
    "Smart Search",
    "Red Flag Checker",
    "Compare & Calculate",
    "Email Draft",
])


with tab_search:
    st.subheader("Describe What You Need")
    natural_query = st.text_area(
        "Tell us in your own words:",
        placeholder="e.g., I want a 2-bed flat under £1,800, pet-friendly, within 30 minutes of Canary Wharf.",
        height=100,
    )
    if st.button("Parse My Requirements", key="parse_btn"):
        if not natural_query.strip():
            st.warning("Please enter your requirements first.")
        else:
            with st.spinner("Thinking..."):
                parser = RequirementParser()
                constraints = parser.parse(natural_query)

            # Show parsed constraints
            st.markdown("#### Parsed Constraints")
            st.json(constraints)

            # Show constraint warnings
            if constraints.get("constraint_warnings"):
                for warning in constraints["constraint_warnings"]:
                    st.warning(warning)

            # Show suggested zones / boroughs
            suggested = constraints.get("suggested_zones", [])
            if suggested:
                with st.container(border=True):
                    st.markdown("#### Consider These Areas")
                    for zone in suggested:
                        name = zone.get("name", "Unknown area")
                        rationale = zone.get("rationale", "")
                        st.markdown(f"- **{name}** — {rationale}")

            # Filter listings
            matched, excluded = filter_listings(constraints, listings)

            st.markdown("---")
            if matched:
                st.success(f"Found {len(matched)} matching listing(s)")
                for m in matched:
                    st.markdown(f"- **{m['title']}** — £{m['price_pcm']}/mo — {m['location_postcode']}")
                    tags = m.get("match_tags", [])
                    if tags:
                        st.caption(f"Matched: {' · '.join(tags)}")
            else:
                msg = "No listings match your requirements. Try relaxing budget or bedroom count."
                if suggested:
                    zone_names = ", ".join(z.get("name", "") for z in suggested)
                    msg += f" Alternatively, explore listings in {zone_names}."
                st.warning(msg)

            if excluded:
                with st.expander(f"See {len(excluded)} excluded listings"):
                    for e in excluded:
                        st.markdown(f"**{e['title']}**: {', '.join(e['reasons'])}")


with tab_flags:
    st.subheader("Check a Listing for Red Flags")
    selected_listing = st.selectbox(
        "Choose a listing to analyze:",
        options=[(l["id"], f"{l['title']} — £{l['price_pcm']}/mo") for l in listings],
        format_func=lambda x: x[1],
    )
    if selected_listing:
        listing_id = selected_listing[0]
        listing = next((l for l in listings if l["id"] == listing_id), None)
        if listing is None:
            st.error("Listing not found.")
        else:
            st.markdown(f"**Title**: {listing['title']}")
            st.markdown(f"**Description**: {listing['description']}")
            st.markdown(f"**Price**: £{listing['price_pcm']}/month | **Location**: {listing['location_postcode']}")

            if st.button("Analyze for Red Flags", key="flag_btn"):
                with st.spinner("Scanning..."):
                    detector = RedFlagDetector()
                    result = detector.analyze(listing)

                if result.get("overall_risk") == "unknown":
                    st.error("Could not complete analysis. Check API key and connection.")
                else:
                    risk = result.get("overall_risk", "low")
                    risk_emoji = {"low": "[Low]", "medium": "[Medium]", "high": "[High]"}.get(risk, "[Unknown]")

                    # SCAM banner
                    flags = result.get("flags", [])
                    scam_flags = [f for f in flags if f.get("category") == "SCAM_RISK" and f.get("severity") == "high"]
                    if scam_flags:
                        st.error("**HIGH RISK: Potential Scam Detected** — Do not send money before viewing.")

                    st.markdown(f"### Overall Risk: {risk_emoji} {risk.upper()}")

                    if flags:
                        for flag in flags:
                            sev = flag.get("severity", "low").upper()
                            cat = flag.get("category", "")
                            evidence = flag.get("evidence", "")
                            explanation = flag.get("explanation", "")
                            recommendation = flag.get("recommendation", "")

                            with st.container(border=True):
                                st.markdown(f"**{cat}** — Severity: `{sev}`")
                                st.markdown(f"> *Evidence:* \"{evidence}\"")
                                st.markdown(f"{explanation}")
                                if recommendation:
                                    st.markdown(f"*{recommendation}*")
                    else:
                        st.success("No red flags detected. This listing appears normal, but always verify in person.")

                    missing = result.get("missing_info", [])
                    if missing:
                        with st.expander("Missing Information"):
                            for m in missing:
                                st.markdown(f"- {m}")


with tab_compare:
    st.subheader("True Cost Comparison")
    st.markdown("Select up to 3 listings to compare total monthly outlay.")

    calc = CostCalculator()
    work_zone = st.selectbox(
        "Your work location TfL zone:",
        options=["1", "2", "3", "4", "5", "6"],
        index=0,
    )

    selected_ids = st.multiselect(
        "Select listings:",
        options=[l["id"] for l in listings],
        format_func=lambda x: next((f"{l['title']} — £{l['price_pcm']}/mo" for l in listings if l["id"] == x), "Unknown listing"),
        max_selections=3,
    )

    if selected_ids:
        results = []
        for lid in selected_ids:
            listing = next((l for l in listings if l["id"] == lid), None)
            if listing is None:
                continue
            cost = calc.calculate_true_cost(listing, work_zone=work_zone)
            results.append({"listing": listing, "cost": cost})

        st.markdown("---")

        # Side-by-side metrics
        cols = st.columns(len(results))
        for idx, col in enumerate(cols):
            r = results[idx]
            listing = r["listing"]
            cost = r["cost"]
            with col:
                st.markdown(f"**{listing['title']}**")
                st.metric("True Monthly Cost", f"£{cost['true_cost']}")

        st.markdown("---")

        # Detailed breakdown table
        st.markdown("#### Cost Breakdown")
        breakdown_data = []
        for r in results:
            listing = r["listing"]
            cost = r["cost"]
            utilities_display = "Included" if listing.get("bills_included") else f"£{cost['utilities']}"
            breakdown_data.append({
                "Listing": listing["title"][:25] + "..." if len(listing["title"]) > 25 else listing["title"],
                "Rent": f"£{cost['rent']}",
                "Council Tax": f"£{cost['council_tax']}",
                "Commute": f"£{cost['commute']}",
                "Utilities": utilities_display,
                "True Cost": f"£{cost['true_cost']}",
            })

        st.table(breakdown_data)

        # Disclaimer
        st.caption("Council tax estimate is based on Band C-D midpoint when band is unknown. Verify with landlord.")

        st.markdown("---")
        st.subheader("AI Comparison Summary")

        with st.spinner("Analyzing trade-offs..."):
            comparator = ComparisonGenerator()
            comparison = comparator.compare(results)

        # Summary card
        with st.container(border=True):
            summary = comparison.get("summary", "")
            if isinstance(summary, list):
                for line in summary:
                    st.markdown(line)
            else:
                st.markdown(summary)

        # Trade-offs card
        if comparison.get("trade_offs"):
            with st.container(border=True):
                st.markdown("**Trade-offs**")
                for to in comparison["trade_offs"]:
                    st.markdown(f"- **{to['dimension'].title()}**: {to['comparison']}")

        # Winner cards
        win_col1, win_col2 = st.columns(2)
        with win_col1:
            wb = comparison.get("winner_for_budget", "tie")
            with st.container(border=True):
                if wb != "tie":
                    winner = next((r for r in results if r["listing"]["id"] == wb), None)
                    if winner:
                        st.success(f"Best for Budget\n\n**{winner['listing']['title']}**\n£{winner['cost']['true_cost']}/mo")
                else:
                    st.info("Budget: Tie\n\nAll selected listings have similar total costs.")

        with win_col2:
            wc = comparison.get("winner_for_commute", "tie")
            with st.container(border=True):
                if wc != "tie":
                    winner = next((r for r in results if r["listing"]["id"] == wc), None)
                    if winner:
                        st.success(f"Best for Commute\n\n**{winner['listing']['title']}**\n£{winner['cost']['commute']}/mo")
                else:
                    st.info("Commute: Tie\n\nAll selected listings have similar commute costs.")

        # Caveats card
        if comparison.get("caveats"):
            with st.container(border=True):
                st.markdown("**Caveats**")
                for caveat in comparison["caveats"]:
                    st.markdown(f"- {caveat}")


with tab_email:
    st.subheader("Draft an Enquiry Email")
    st.markdown("Select a listing and tell us about yourself. We'll generate a personalised draft.")

    if "email_draft" not in st.session_state:
        st.session_state.email_draft = None

    email_listing = st.selectbox(
        "Choose a listing:",
        options=[(l["id"], f"{l['title']} — £{l['price_pcm']}/mo") for l in listings],
        format_func=lambda x: x[1],
        key="email_listing_select",
    )

    if email_listing:
        listing_id = email_listing[0]
        # Clear draft when user switches to a different listing
        if st.session_state.get("last_email_listing_id") != listing_id:
            st.session_state.email_draft = None
            st.session_state.last_email_listing_id = listing_id

        listing = next((l for l in listings if l["id"] == listing_id), None)
        if listing is None:
            st.error("Listing not found.")
        else:
            st.markdown("---")
            st.markdown("**Your Profile**")

            col1, col2 = st.columns(2)
            with col1:
                persona = st.radio(
                    "I am a:",
                    options=["young professional", "student", "family"],
                    horizontal=True,
                )
            with col2:
                move_in_date = st.text_input("Move-in date:", value="1st July 2026")
                has_pets = st.checkbox("I have pets")

            col_gen, col_regen = st.columns(2)
            with col_gen:
                generate_clicked = st.button("Generate Draft", key="email_btn")
            with col_regen:
                regen_clicked = st.button("Regenerate", key="regen_btn")
                if not st.session_state.email_draft:
                    regen_clicked = False

            if generate_clicked or regen_clicked:
                with st.spinner("Drafting..."):
                    # Get red flags first (needed for adaptive logic)
                    detector = RedFlagDetector()
                    red_flags = detector.analyze(listing)

                    user_profile = {
                        "persona": persona,
                        "move_in_date": move_in_date,
                        "has_pets": has_pets,
                    }

                    drafter = InquiryDrafter()
                    st.session_state.email_draft = drafter.draft(listing, red_flags, user_profile)

            if st.session_state.email_draft:
                st.markdown("---")
                st.markdown("#### Email Draft")
                st.code(st.session_state.email_draft, language="text")

                st.info("This is an AI-generated draft. Please review and personalise before sending.")


st.divider()
st.caption("Built as a side project for AI Product internship applications. Data is sample only.")
