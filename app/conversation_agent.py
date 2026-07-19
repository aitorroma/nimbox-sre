from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import AnalysisContext, SimulationBundle
from .report_builder import generate_report_pdf
from .simulator import (
    build_current_scenario,
    build_proposal_scenario,
    estimate_power_cost,
    normalize_period_map,
    resolve_comparison,
)

logger = logging.getLogger("nimelectric-bot.conversation")

try:
    from agno.agent import Agent
    from agno.models.openai.like import OpenAILike
except Exception:  # pragma: no cover
    Agent = None
    OpenAILike = None

_INSTRUCTIONS = [
    "Eres el asistente de NimElectric para análisis y ahorro energético eléctrico en España.",
    "Ayudas a clientes a entender su factura eléctrica y encontrar comercializadoras más baratas.",
    "Cuando el usuario pida simular, comparar o probar con una comercializadora, usa simulate_proposal.",
    "Cuando el usuario pida el informe o el PDF, usa generate_report.",
    "Si necesitas datos de la factura actualmente cargada, usa get_invoice_summary.",
    "Si no hay factura cargada, pide al usuario que suba un PDF.",
    "Responde siempre en español, de forma clara y concisa.",
    "No inventes precios ni datos que no te hayan proporcionado.",
]


def build_conversation_agent(
    chat_id,
    store,
    telegram_client,
    output_dir: Path,
    api_key: str,
    base_url: str,
    model_id: str,
) -> "Agent":
    if Agent is None or OpenAILike is None:
        raise RuntimeError("agno no está instalado")

    def get_invoice_summary() -> str:
        """Obtiene el resumen del análisis actual: cliente, CUPS, tarifa, consumo, costes y simulación disponible."""
        state = store.get(chat_id)
        if "analysis_context" not in state:
            return "No hay ninguna factura analizada. Pide al usuario que envíe un PDF."
        ctx = AnalysisContext.model_validate(state["analysis_context"])
        inv = ctx.invoice
        enr = ctx.enrichment
        sim = ctx.simulation

        parts: list[str] = []
        if inv.customer_name:
            parts.append(f"Cliente: {inv.customer_name}")
        if inv.cups:
            parts.append(f"CUPS: {inv.cups}")
        tariff = inv.tariff or (enr.atr_tariff if enr else None)
        if tariff:
            parts.append(f"Tarifa: {tariff}")
        kwh = (enr.annual_total_kwh if enr else None) or inv.annual_consumption_kwh
        if kwh:
            parts.append(f"Consumo anual: {kwh:,.0f} kWh".replace(",", "."))
        if inv.supplier_name:
            parts.append(f"Comercializadora actual: {inv.supplier_name}")
        power = (enr.contracted_power_kw if enr else None) or inv.power_periods_kw
        if power:
            parts.append(f"Potencias contratadas: {dict(power)}")
        if sim and sim.current and sim.current.selected_annual_total:
            parts.append(f"Coste anual actual estimado: {sim.current.selected_annual_total:.2f} €")
        if sim and sim.best_proposal and sim.best_proposal.selected_annual_total:
            parts.append(f"Mejor propuesta: {sim.best_proposal.supplier_name} – {sim.best_proposal.selected_annual_total:.2f} €/año")
        if sim and sim.comparison and sim.comparison.annual_savings:
            pct = sim.comparison.savings_percent or 0
            parts.append(f"Ahorro estimado: {sim.comparison.annual_savings:.2f} € ({pct:.1f}%)")
        return "\n".join(parts) if parts else "No hay datos de la factura disponibles."

    def simulate_proposal(
        supplier_name: str,
        energy_price_eur_kwh: float,
        proposed_powers_kw: str | None = None,
    ) -> str:
        """
        Simula el coste anual con una comercializadora y precio de energía concretos.

        Args:
            supplier_name: Nombre de la comercializadora (ej: 'AXPO', 'Naturgy', 'Endesa').
            energy_price_eur_kwh: Precio de la energía en €/kWh (ej: 0.122).
            proposed_powers_kw: JSON con potencias propuestas por periodo, ej:
                '{"P1":15,"P2":15,"P3":15,"P4":15,"P5":15,"P6":35}'.
                Omitir o null para mantener las potencias actuales.
        """
        state = store.get(chat_id)
        if "analysis_context" not in state:
            return "No hay factura cargada. Pide al usuario que suba un PDF."

        ctx = AnalysisContext.model_validate(state["analysis_context"])
        inv = ctx.invoice
        enr = ctx.enrichment

        current_power = normalize_period_map(
            (enr.contracted_power_kw if enr else None) or inv.power_periods_kw
        )
        power_rates: dict[str, float] = {}
        if ctx.simulation and ctx.simulation.best_proposal and ctx.simulation.best_proposal.power_rates_eur_kw_day:
            power_rates = ctx.simulation.best_proposal.power_rates_eur_kw_day
        if not power_rates and inv.power_rates_eur_kw_day:
            power_rates = inv.power_rates_eur_kw_day

        proposed_powers: dict[str, float] | None = None
        if proposed_powers_kw:
            try:
                proposed_powers = json.loads(proposed_powers_kw)
            except Exception:
                pass

        price_components: dict = {}
        for i in range(1, 7):
            price_components[f"c_p{i}_eur_kwh"] = energy_price_eur_kwh
        for k, v in power_rates.items():
            idx = k.replace("P", "")
            price_components[f"p{idx}_eur_kw_day"] = v

        offer: dict = {
            "supplier_name": supplier_name,
            "name": f"{supplier_name} — simulación manual",
            "price_components": price_components,
        }

        if proposed_powers and power_rates:
            normalized_proposed = normalize_period_map(proposed_powers)
            est_power = estimate_power_cost(normalized_proposed, power_rates)
            if est_power is not None:
                offer["estimated_power_eur"] = est_power

        current_scenario = build_current_scenario(ctx)
        proposal_scenario = build_proposal_scenario(ctx, offer)

        if proposed_powers:
            proposal_scenario.proposed_power_kw = normalize_period_map(proposed_powers)

        comparison = resolve_comparison(current_scenario, proposal_scenario)

        ctx.simulation = SimulationBundle(
            current=current_scenario,
            proposals=[proposal_scenario],
            best_proposal=proposal_scenario,
            comparison=comparison,
        )
        state["analysis_context"] = ctx.model_dump(mode="json")
        store.set(chat_id, state)

        c_total = current_scenario.selected_annual_total or 0
        p_total = proposal_scenario.selected_annual_total or 0
        savings = comparison.annual_savings
        pct = comparison.savings_percent or 0

        lines = [
            f"Simulación: {supplier_name} a {energy_price_eur_kwh:.5f} €/kWh",
            f"• Coste actual estimado: {c_total:,.2f} €/año".replace(",", "."),
            f"• Coste propuesto: {p_total:,.2f} €/año".replace(",", "."),
            f"• Ahorro estimado: {savings:,.2f} € ({pct:.1f}%)".replace(",", "."),
        ]
        if proposed_powers:
            powers_str = ", ".join(
                f"{k}:{v}" for k, v in sorted(normalize_period_map(proposed_powers).items())
            )
            lines.append(f"• Potencias propuestas: {powers_str}")
        lines.append("\n¿Quieres que genere el informe PDF con esta propuesta?")
        return "\n".join(lines)

    def generate_report() -> str:
        """Genera el informe PDF de ahorro energético con la propuesta actual y lo envía al usuario por Telegram."""
        state = store.get(chat_id)
        if "analysis_context" not in state:
            return "No hay factura cargada."
        ctx = AnalysisContext.model_validate(state["analysis_context"])
        if not ctx.enrichment:
            return "Faltan datos del CUPS. El CUPS debe estar validado para generar el informe."
        if not ctx.simulation or not ctx.simulation.best_proposal:
            return "No hay propuesta simulada aún. Usa simulate_proposal para crear una."
        try:
            out_dir = output_dir / str(chat_id)
            pdf_path, _ = generate_report_pdf(ctx, out_dir)
            telegram_client.send_document(chat_id, str(pdf_path), "📊 Informe NimElectric")
            return f"Informe generado y enviado: {pdf_path.name}"
        except Exception as exc:
            logger.exception("Error generating report for chat_id=%s", chat_id)
            return f"Error al generar el informe: {exc}"

    return Agent(
        name="NimElectric Assistant",
        model=OpenAILike(id=model_id, api_key=api_key, base_url=base_url),
        tools=[get_invoice_summary, simulate_proposal, generate_report],
        markdown=False,
        instructions=_INSTRUCTIONS,
    )


def is_configured(api_key: str | None, base_url: str | None, model_id: str | None) -> bool:
    return bool(api_key and base_url and model_id and Agent is not None and OpenAILike is not None)
