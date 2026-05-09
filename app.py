import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import time

# Importamos nuestros módulos locales
from src.services.pricing import PriceService
from src.services.snapshot import SnapshotService
from src.models.portfolio import Portfolio
from src.utils.storage import LocalStorage
from src.utils.format import format_qty

# ───────── CONFIGURACIÓN DE PÁGINA (mejorada) ─────────
st.set_page_config(
    page_title="Amygdalé · Second Brain Finance",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ───────── CSS PERSONALIZADO (mejoras visuales) ─────────
st.markdown("""
<style>
    /* Fuente y fondo general */
    .stApp {
        background-color: #f8fafc;
    }
    /* Tarjetas de métricas */
    .metric-card {
        background: white;
        border-radius: 20px;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s;
        border: 1px solid #e2e8f0;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #475569;
        letter-spacing: 0.02em;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .metric-delta {
        font-size: 0.8rem;
        margin-top: 0.25rem;
    }
    /* Tabla estilizada */
    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    /* Botones más redondeados */
    .stButton button {
        border-radius: 40px !important;
        font-weight: 500 !important;
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: scale(1.01);
    }
    /* Sidebar más elegante */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    /* Inputs redondeados */
    input, select, textarea {
        border-radius: 12px !important;
    }
    /* Títulos */
    h1, h2, h3 {
        font-weight: 600 !important;
    }
    /* Spinner personalizado */
    .stSpinner > div {
        border-top-color: #3b82f6 !important;
    }
    /* Ocultar "made with streamlit" */
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ───────── INICIALIZACIÓN DE SERVICIOS ─────────
@st.cache_resource
def load_services():
    storage = LocalStorage()
    pricing = PriceService()
    snapshot = SnapshotService()
    return storage, pricing, snapshot

storage, pricing_service, snapshot_service = load_services()

# ───────── ESTADO DE SESIÓN ─────────
if "portfolio" not in st.session_state:
    positions_data = storage.load_positions()
    portfolio = Portfolio()
    if positions_data and isinstance(positions_data, list):
        for pos_dict in positions_data:
            ticker = pos_dict.get('ticker')
            asset_type = pos_dict.get('asset_type')
            holdings = pos_dict.get('holdings', [])
            if ticker and asset_type and holdings:
                for h in holdings:
                    portfolio.add_position(
                        ticker=ticker,
                        asset_type=asset_type,
                        qty=float(h.get('qty', 0)),
                        ppc=float(h.get('price', 0)),
                        tc=float(h.get('tc')) if h.get('tc') is not None else None
                    )
    st.session_state.portfolio = portfolio

portfolio = st.session_state.portfolio

# ───────── SIDEBAR: AGREGAR POSICIÓN ─────────
with st.sidebar:
    st.markdown("### 🧠 Amygdalé")
    st.markdown("---")
    st.markdown("#### ➕ Nueva posición")
    
    ticker = st.text_input("Ticker", placeholder="Ej: AL30, AAPL, BTC").upper()
    asset_type = st.selectbox("Tipo", ["Argentina", "Global", "Cripto"])
    qty = st.number_input("Cantidad", min_value=0.0001, step=0.01, format="%.4f")
    ppc = st.number_input("Precio prom. compra (USD / ARS según tipo)", min_value=0.01, step=0.01, format="%.2f")
    
    if st.button("➕ Agregar posición", type="primary", use_container_width=True):
        if ticker and qty > 0 and ppc > 0:
            type_map = {"Argentina": "ar", "Global": "global", "Cripto": "crypto"}
            selected_type = type_map[asset_type]
            
            with st.spinner("Verificando precio MEP..."):
                current_mep = None
                if selected_type == 'ar':
                    try:
                        current_mep = pricing_service.get_mep_rate()
                    except Exception as e:
                        st.warning(f"No se pudo obtener MEP: {e}")
            
            portfolio.add_position(ticker, selected_type, qty, ppc, tc=current_mep)
            
            # Guardar en disco
            positions_to_save = []
            for p in portfolio.positions:
                holdings_list = [{'qty': h.qty, 'price': h.price, 'date': h.date.isoformat(), 'tc': h.tc} for h in p.holdings]
                positions_to_save.append({'ticker': p.ticker, 'asset_type': p.asset_type, 'holdings': holdings_list})
            storage.save_positions(positions_to_save)
            
            st.success(f"✅ {ticker} agregado correctamente")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("❌ Completá todos los campos con valores válidos")
    
    st.markdown("---")
    st.caption("v1.1 · Datos locales · Open source")

# ───────── OBTENER PRECIOS (con manejo de errores) ─────────
if portfolio.positions:
    with st.spinner("🔄 Actualizando precios en tiempo real..."):
        try:
            prices = pricing_service.get_prices_batch(portfolio.positions)
            if prices:
                portfolio.update_prices(prices)
            else:
                st.warning("⚠️ No se pudieron obtener precios actualizados. Mostrando últimos conocidos.")
        except Exception as e:
            st.error(f"❌ Error al actualizar precios: {e}")

# ───────── CALCULAR MÉTRICAS GLOBALES (una sola vez) ─────────
try:
    mep_rate = pricing_service.get_mep_rate()
    if mep_rate is None or mep_rate == 0:
        mep_rate = 1.0
        st.info("ℹ️ Tasa MEP no disponible, usando 1:1 para activos argentinos.")
except:
    mep_rate = 1.0

total_usd = 0.0
total_pnl_usd = 0.0
total_cost_usd = 0.0
best_performer = None
best_change = -float('inf')

for p in portfolio.positions:
    # Valor actual
    val_orig = p.current_value_original if p.current_value_original is not None else 0.0
    divisor = mep_rate if p.asset_type == 'ar' else 1.0
    if divisor == 0:
        divisor = 1.0
    val_usd = val_orig / divisor
    
    # Costo
    avg_cost = p.avg_cost_original if p.avg_cost_original is not None else 0.0
    total_qty = p.total_qty if p.total_qty is not None else 0.0
    cost_orig = avg_cost * total_qty
    cost_usd = cost_orig / divisor
    
    pnl_usd = val_usd - cost_usd
    
    total_usd += val_usd
    total_pnl_usd += pnl_usd
    total_cost_usd += cost_usd
    
    change_pct = p.change_pct if p.change_pct is not None else -float('inf')
    if change_pct > best_change:
        best_change = change_pct
        best_performer = p

total_pnl_pct = (total_pnl_usd / total_cost_usd * 100) if total_cost_usd > 0 else 0.0

# ───────── HEADER ─────────
st.title("🧠 Amygdalé")
st.markdown("*Second Brain Financial Control* – Seguí tu patrimonio en USD con datos en tiempo real.")
st.markdown("---")

# ───────── MÉTRICAS (con CSS custom) ─────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💰 Valor total</div>
        <div class="metric-value">${total_usd:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    delta_color = "green" if total_pnl_usd >= 0 else "red"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">📈 Ganancia total</div>
        <div class="metric-value" style="color:{delta_color};">${total_pnl_usd:,.2f}</div>
        <div class="metric-delta" style="color:{delta_color};">{total_pnl_pct:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">📦 Posiciones activas</div>
        <div class="metric-value">{len(portfolio.positions)}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    if best_performer:
        perf_color = "green" if best_change >= 0 else "red"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🏆 Mejor hoy</div>
            <div class="metric-value">{best_performer.ticker}</div>
            <div class="metric-delta" style="color:{perf_color};">{best_change:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🏆 Mejor hoy</div>
            <div class="metric-value">—</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ───────── GRÁFICOS ─────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("🥧 Composición del portfolio")
    if portfolio.positions:
        data_pie = []
        for p in portfolio.positions:
            val_orig = p.current_value_original if p.current_value_original is not None else 0.0
            divisor_pie = mep_rate if p.asset_type == 'ar' else 1.0
            if divisor_pie == 0: divisor_pie = 1.0
            val_usd = val_orig / divisor_pie
            data_pie.append({"Activo": p.ticker, "Valor USD": val_usd})
        df_pie = pd.DataFrame(data_pie)
        if not df_pie.empty and df_pie["Valor USD"].sum() > 0:
            fig_pie = px.pie(df_pie, values="Valor USD", names="Activo", hole=0.6,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label',
                                  hoverinfo='label+percent+value')
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=400,
                                  showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay datos suficientes para el gráfico.")
    else:
        st.info("Agregá posiciones para ver la distribución.")

with chart_col2:
    st.subheader("📈 Evolución vs. Benchmark (30d)")
    try:
        history = snapshot_service.get_history(days=30)
    except Exception as e:
        history = []
        st.warning(f"No se pudo cargar histórico: {e}")
    
    if history and len(history) >= 2:
        df_hist = pd.DataFrame(history)
        df_hist['date'] = pd.to_datetime(df_hist['date'])
        if 'totalUSD' in df_hist.columns and 'benchmark' in df_hist.columns:
            fig_line = px.line(df_hist, x='date', y=['totalUSD', 'benchmark'],
                               labels={'value': 'USD', 'variable': ''},
                               color_discrete_map={'totalUSD': '#3b82f6', 'benchmark': '#10b981'})
            fig_line.update_layout(margin=dict(t=20, b=20), height=400,
                                   hovermode='x unified', xaxis_tickformat='%d/%m')
            fig_line.update_traces(line=dict(width=2.5))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.caption("Formato de histórico incorrecto.")
    else:
        st.caption("📊 Se necesitan al menos 2 días de datos para mostrar evolución.")

# ───────── TABLA DE POSICIONES (mejorada) ─────────
st.subheader("📋 Detalle de posiciones")
if portfolio.positions:
    table_data = []
    for p in portfolio.positions:
        # Reutilizamos cálculos locales para evitar repetición
        val_orig = p.current_value_original if p.current_value_original is not None else 0.0
        divisor = mep_rate if p.asset_type == 'ar' else 1.0
        if divisor == 0: divisor = 1.0
        val_usd = val_orig / divisor
        
        avg_cost_orig = p.avg_cost_original if p.avg_cost_original is not None else 0.0
        total_qty = p.total_qty if p.total_qty is not None else 0.0
        cost_orig = avg_cost_orig * total_qty
        cost_usd = cost_orig / divisor
        pnl_usd = val_usd - cost_usd
        per = (pnl_usd / cost_usd * 100) if cost_usd > 0.01 else 0.0
        
        ppc_usd = (avg_cost_orig / divisor) if avg_cost_orig > 0 else 0.0
        current_price_usd = (p.current_price / divisor) if p.current_price is not None else 0.0
        change_pct = p.change_pct if p.change_pct is not None else 0.0
        
        table_data.append({
            "Ticker": p.ticker,
            "Tipo": p.asset_type.upper(),
            "Cantidad": format_qty(total_qty),
            "PPC (USD)": f"${ppc_usd:,.2f}",
            "Precio (USD)": f"${current_price_usd:,.2f}",
            "Var %": f"{change_pct:+.2f}%",
            "Valor (USD)": f"${val_usd:,.2f}",
            "P&L (USD)": f"${pnl_usd:,.2f}",
            "PER %": f"{per:+.2f}%"
        })
    
    df_table = pd.DataFrame(table_data)
    
    # Función de estilo mejorada (colores más suaves)
    def style_pnl(val):
        if isinstance(val, str):
            if val.startswith('-') or '−' in val:
                return 'color: #ef4444; font-weight: 500'
            elif val.startswith('+'):
                return 'color: #10b981; font-weight: 500'
        return ''
    
    styled = df_table.style.map(style_pnl, subset=['Var %', 'P&L (USD)', 'PER %'])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("📭 No hay posiciones activas. Usá el sidebar para agregar tu primera inversión.")

# ───────── FOOTER: EXPORTAR / IMPORTAR ─────────
st.markdown("---")
exp_col, imp_col = st.columns(2)

with exp_col:
    if st.button("📥 Exportar backup (JSON)", use_container_width=True):
        export_data = []
        for p in portfolio.positions:
            holdings_list = [{'qty': h.qty, 'price': h.price, 'date': h.date.isoformat(), 'tc': h.tc} for h in p.holdings]
            export_data.append({'ticker': p.ticker, 'asset_type': p.asset_type, 'holdings': holdings_list})
        
        full_backup = {
            "positions": export_data,
            "history": snapshot_service.history if hasattr(snapshot_service, 'history') else [],
            "exported_at": datetime.now().isoformat()
        }
        json_str = json.dumps(full_backup, indent=2, ensure_ascii=False)
        st.download_button("⬇️ Descargar archivo", data=json_str,
                           file_name=f"amygdale_backup_{datetime.now().date()}.json",
                           mime="application/json", use_container_width=True)

with imp_col:
    uploaded = st.file_uploader("📤 Importar backup", type=["json"], label_visibility="collapsed")
    if uploaded:
        try:
            data = json.loads(uploaded.read().decode("utf-8"))
            if "positions" in data and isinstance(data["positions"], list):
                # Reemplazar portfolio existente
                new_portfolio = Portfolio()
                for pos_dict in data["positions"]:
                    ticker = pos_dict.get('ticker')
                    asset_type = pos_dict.get('asset_type')
                    for h in pos_dict.get('holdings', []):
                        new_portfolio.add_position(
                            ticker=ticker,
                            asset_type=asset_type,
                            qty=float(h.get('qty', 0)),
                            ppc=float(h.get('price', 0)),
                            tc=float(h.get('tc')) if h.get('tc') is not None else None
                        )
                st.session_state.portfolio = new_portfolio
                storage.save_positions(data["positions"])
                if "history" in data and hasattr(snapshot_service, 'history'):
                    snapshot_service.history = data["history"]
                    if hasattr(snapshot_service, '_save_history'):
                        snapshot_service._save_history()
                st.success("✅ Portfolio importado correctamente. Recargando...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ El archivo no contiene una lista de posiciones válida.")
        except Exception as e:
            st.error(f"❌ Error en la importación: {e}")

# ───────── SNAPSHOT DIARIO ─────────
if portfolio.positions and total_usd > 0:
    try:
        snapshot_service.save_snapshot(total_usd, mep_rate)
    except Exception as e:
        pass  # No molestar al usuario con errores de snapshot