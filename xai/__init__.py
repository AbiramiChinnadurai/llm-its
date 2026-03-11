# xai/__init__.py
from xai.xai_engine import (
    build_xai_explanation,
    explain_counterfactual,
    explain_from_kg,
    explain_from_mastery,
    explain_from_emotion,
    generate_cot_explanation,
    get_xai_system_note,
    XAIExplanation,
    CounterfactualExplanation,
)
from xai.xai_widget import (
    render_xai_panel,
    render_xai_strip,
    render_counterfactual,
    render_plan_xai_card,
    render_xai_sidebar,
)
