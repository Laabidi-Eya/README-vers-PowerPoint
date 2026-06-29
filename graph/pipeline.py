from langgraph.graph import StateGraph, END
from agents.parser_agent import parser_agent
from agents.branding_agent import branding_agent
from agents.chart_agent import chart_agent
from agents.pptx_agent import pptx_agent
from typing import TypedDict, Optional

class State(TypedDict):
    readme_content: str
    slides_plan: dict
    output_path: str
    lang: str
    audience: str
    logo_path: Optional[str]
    brand_colors: Optional[dict]
    design_params: Optional[dict]
    effective_colors: Optional[dict]
    chart_data: Optional[dict]

def build_graph():
    graph = StateGraph(State)

    graph.add_node("parser", parser_agent)
    graph.add_node("branding", branding_agent)
    graph.add_node("chart", chart_agent)
    graph.add_node("pptx_builder", pptx_agent)

    graph.set_entry_point("parser")
    graph.add_edge("parser", "branding")
    graph.add_edge("branding", "chart")
    graph.add_edge("chart", "pptx_builder")
    graph.add_edge("pptx_builder", END)

    return graph.compile()