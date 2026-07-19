from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
from typing import Any

from .models import AnalysisContext

SCRIPT_PATH = Path(__file__).resolve().parent / "report" / "scripts" / "nimelectric_report.py"
ASSETS_DIR = Path(__file__).resolve().parent / "report" / "assets"


def _load_report_script():
    spec = importlib.util.spec_from_file_location("nimelectric_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _annualize(value: float | None, days: int | None) -> float:
    if value is None:
        return 0.0
    factor = 365 / days if days and days > 0 else 12
    return round(value * factor, 2)


def _normalize_tariff(tariff: str | None, enrichment_tariff: str | None) -> str:
    return (tariff or enrichment_tariff or "2.0TD").replace(" ", "")


def _map_consumption_for_report(tariff: str, periods: dict[str, float]) -> dict[str, float]:
    if tariff == "2.0TD":
        return {
            "Punta-Llano": round((periods.get("P1", 0.0) + periods.get("P2", 0.0)), 2),
            "Valle": round(periods.get("P3", 0.0), 2),
        }
    return {f"P{i}": round(periods.get(f"P{i}", 0.0), 2) for i in range(1, 7)}


def _map_power_for_report(tariff: str, periods: dict[str, float]) -> dict[str, float]:
    if tariff == "2.0TD":
        return {
            "Punta-Llano": round(periods.get("P1", periods.get("P2", 0.0)), 3),
            "Valle": round(periods.get("P2", periods.get("P1", 0.0)), 3),
        }
    return {f"P{i}": round(periods.get(f"P{i}", 0.0), 3) for i in range(1, 7)}


def build_report_payload(context: AnalysisContext) -> dict[str, Any]:
    if not context.enrichment:
        raise ValueError("Missing enrichment for report generation")

    invoice = context.invoice
    enrichment = context.enrichment
    simulation = context.simulation
    current = simulation.current if simulation else None
    best = simulation.best_proposal if simulation else None
    comparison = simulation.comparison if simulation else None

    tariff = _normalize_tariff(invoice.tariff, enrichment.atr_tariff)
    annual_total = (current.annual_consumption_kwh if current else None) or enrichment.annual_total_kwh or invoice.annual_consumption_kwh or 0.0
    annual_periods = (current.annual_breakdown_kwh if current else None) or enrichment.annual_breakdown_kwh or invoice.energy_periods_kwh
    power_periods = (current.contracted_power_kw if current else None) or enrichment.contracted_power_kw or invoice.power_periods_kw
    billing_days = invoice.billing_days or enrichment.days or 30

    actual_energy = round((current.estimated_energy_cost if current and current.estimated_energy_cost is not None else _annualize(invoice.energy_cost_eur, billing_days)), 2)
    actual_power = round((current.estimated_power_cost if current and current.estimated_power_cost is not None else _annualize(invoice.power_cost_eur, billing_days)), 2)
    actual_tax = round((current.estimated_electricity_tax if current and current.estimated_electricity_tax is not None else _annualize(invoice.electricity_tax_eur, billing_days)), 2)
    actual_vat = round((current.estimated_vat if current and current.estimated_vat is not None else _annualize(invoice.vat_eur, billing_days)), 2)
    actual_other = round((current.estimated_other_cost if current else _annualize(invoice.other_costs_eur, billing_days) + _annualize(invoice.discounts_eur, billing_days)), 2)
    actual_total = round((current.selected_annual_total if current and current.selected_annual_total is not None else _annualize(invoice.total_invoice_eur, billing_days)), 2)

    if actual_total == 0 and invoice.total_invoice_eur:
        actual_total = round(invoice.total_invoice_eur * 12, 2)
    if actual_total == 0:
        actual_total = round(actual_energy + actual_power + actual_tax + actual_vat + actual_other, 2)

    estimated_total = round((best.selected_annual_total if best and best.selected_annual_total is not None else 0.0), 2)
    estimated_energy = round((best.estimated_energy_cost if best and best.estimated_energy_cost is not None else 0.0), 2)
    estimated_power = round((best.estimated_power_cost if best and best.estimated_power_cost is not None else 0.0), 2)
    estimated_tax = round((best.estimated_electricity_tax if best and best.estimated_electricity_tax is not None else 0.0), 2)
    estimated_vat = round((best.estimated_vat if best and best.estimated_vat is not None else 0.0), 2)
    proposal_other = round((best.estimated_other_cost if best else 0.0) + (best.estimated_fixed_cost if best else 0.0), 2)

    ahorro_total = round(comparison.annual_savings if comparison else max(actual_total - estimated_total, 0.0), 2)
    ahorro_pct = round(comparison.savings_percent if comparison and comparison.savings_percent is not None else ((ahorro_total / actual_total * 100.0) if actual_total else 0.0), 2)

    proposal_period_prices = _map_consumption_for_report(tariff, best.energy_rates_eur_kwh if best else {})
    proposal_power_prices = best.power_rates_eur_kw_day if best else {}
    proposal_power_periods = dict(best.proposed_power_kw) if (best and best.proposed_power_kw) else power_periods

    payload = {
        "cliente": invoice.customer_name or "Cliente NimElectric",
        "cups": enrichment.cups,
        "tarifa": tariff,
        "actual": {
            "comercializadora": invoice.supplier_name or "Actual",
            "potencias": _map_power_for_report(tariff, power_periods),
            "consumo_kwh": round(annual_total, 2),
            "consumo_periodos": _map_consumption_for_report(tariff, annual_periods),
            "precio_energia": round(actual_energy / annual_total, 6) if annual_total else 0.0,
            "precio_es_unico": True,
            "coste_energia": actual_energy,
            "coste_potencia": actual_power,
            "excesos": 0,
            "costes_financieros": 0,
            "otros": actual_other,
            "iee": actual_tax,
            "iva": actual_vat,
            "total": actual_total,
        },
        "propuesta": {
            "comercializadora": best.supplier_name if best else "Propuesta NimElectric",
            "potencias": _map_power_for_report(tariff, proposal_power_periods),
            "precio_energia": round(estimated_energy / annual_total, 6) if annual_total else 0.0,
            "precio_es_unico": not bool(proposal_period_prices),
            "precios_periodo": proposal_period_prices,
            "coste_energia": estimated_energy,
            "coste_potencia": estimated_power,
            "excesos": 0,
            "costes_financieros": 0,
            "otros": proposal_other,
            "iee": estimated_tax,
            "iva": estimated_vat,
            "total": estimated_total,
        },
        "precios_potencia": {
            f"P{i}": float(proposal_power_prices.get(f"P{i}") or 0.0)
            for i in range(1, 7 if tariff == "3.0TD" else 3)
        },
        "ahorro": {
            "total": ahorro_total,
            "pct": ahorro_pct,
            "desglose": [
                {
                    "concepto": "Cambio de comercializadora",
                    "importe": -ahorro_total,
                    "detalle": f"De {invoice.supplier_name or 'actual'} a {best.supplier_name if best else 'propuesta NimElectric'}",
                }
            ],
        },
        "fecha": date.today().strftime("%d/%m/%Y"),
        "periodo": "Proyección anual",
        "frase_cierre": f"Con la propuesta {best.tariff_name if best else 'NimElectric'} se estima un ahorro anual del {ahorro_pct}%.",
    }
    return payload


def generate_report_pdf(context: AnalysisContext, output_dir: Path) -> tuple[Path, dict[str, Any]]:
    report_module = _load_report_script()
    payload = build_report_payload(context)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"informe-{context.enrichment.cups if context.enrichment else 'nimelectric'}.pdf"
    report_module.build(payload, str(output_path))
    return output_path, payload


def save_report_payload(payload: dict[str, Any], output_dir: Path, name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path
