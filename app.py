import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json

# Importamos nuestros módulos locales
from src.services.pricing import PriceService
from src.services.snapshot import SnapshotService
from src.models.portfolio import Portfolio
from src.utils.storage import LocalStorage
from src.utils.format import format_usd, format_ars, format_pct, format_qty, format_weight

# ───────── CONFIGURACIÓN DE PÁGINA ─────────
st.set_page_config(
    page_title="Amygdalé", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ───────── INICIALIZACIÓN DE SERVICIOS ─────────
@st.cache_resource
def load_services():
    """Carga los servicios una sola vez por sesión para mantener el estado y caché."""
    storage = LocalStorage()
    pricing = PriceService()
    snapshot = SnapshotService()
    return storage, pricing, snapshot

storage, pricing_service, snapshot_service = load_services()

# ───────── ESTADO DE SESIÓN (Session State) ─────────
if "portfolio" not in st.session_state:
    # 1. Cargar datos desde JSON local
    positions_data = storage.load_positions()
    
    # 2. Crear instancia del portfolio
    portfolio = Portfolio()
    
    # 3. Reconstruir el portfolio desde los datos guardados
    if positions_data:
        for pos_dict in positions_data:
            ticker = pos_dict.get('ticker')
            asset_type = pos_dict.get('asset_type')
            holdings = pos_dict.get('holdings', [])
            
            if ticker and asset_type:
                for h in holdings:
                    # Recreamos cada compra (holding)
                    portfolio.add_position(
                        ticker=ticker,
                        asset_type=asset_type,
                        qty=float(h.get('qty', 0)),
                        ppc=float(h.get('price', 0)),
                        tc=float(h.get('tc')) if h.get('tc') else None
                    )
    
    st.session_state.portfolio = portfolio

portfolio = st.session_state.portfolio

# ───────── SIDEBAR: AGREGAR POSICIÓN ─────────
with st.sidebar:
    st.header("➕ Agregar Posición")
    
    ticker = st.text_input("Ticker", placeholder="AL30, AAPL, BTC").upper()
    asset_type = st.selectbox("Tipo", ["Argentina", "Global", "Cripto"])
    qty = st.number_input("Cantidad", min_value=0.0001, step=0.01, format="%.4f")
    ppc = st.number_input("Precio Prom. Compra", min_value=0.01, step=0.01, format="%.2f")
    
    if st.button("Agregar", type="primary", use_container_width=True):
        if ticker and qty > 0 and ppc > 0:
            type_map = {"Argentina": "ar", "Global": "global", "Cripto": "crypto"}
            selected_type = type_map[asset_type]
            
            # Obtener tasa MEP actual si es activo argentino para guardar historial
            current_mep = pricing_service.get_mep_rate() if selected_type == 'ar' else None
            
            # Agregar al objeto en memoria
            portfolio.add_position(
                ticker=ticker, 
                asset_type=selected_type, 
                qty=qty, 
                ppc=ppc,
                tc=current_mep
            )
            
            # Guardar en disco inmediatamente
            # Convertimos el objeto Portfolio a una lista de diccionarios serializable
            positions_to_save = []
            for p in portfolio.positions:
                holdings_list = []
                for h in p.holdings:
                    holdings_list.append({
                        'qty': h.qty,
                        'price': h.price,
                        'date': h.date.isoformat(),
                        'tc': h.tc
                    })
                positions_to_save.append({
                    'ticker': p.ticker,
                    'asset_type': p.asset_type,
                    'holdings': holdings_list
                })
            
            storage.save_positions(positions_to_save)
            
            st.success(f"✅ {ticker} agregado correctamente.")
            st.rerun()
        else:
            st.error("❌ Completá todos los campos con valores válidos.")

    st.divider()
    st.caption("Amygdalé v1.0 — Local-First")

# ───────── OBTENER PRECIOS EN TIEMPO REAL ─────────
# Actualizamos los precios del mercado para todas las posiciones actuales
if portfolio.positions:
    prices = pricing_service.get_prices_batch(portfolio.positions)
    portfolio.update_prices(prices)

# ───────── HEADER & MÉTRICAS ─────────
st.title("🧠 Amygdalé")
st.markdown("*Second Brain Financial Control*")

mep_rate = pricing_service.get_mep_rate()

# Calcular métricas globales manualmente para asegurar precisión con el MEP actual
total_usd = 0.0
total_pnl_usd = 0.0
total_cost_usd = 0.0
best_performer = None
best_change = -float('inf')

for p in portfolio.positions:
    # Valor actual
    val_original = p.current_value_original
    val_usd = val_original / mep_rate if p.asset_type == 'ar' else val_original
    
    # Costo
    cost_original = p.avg_cost_original * p.total_qty
    cost_usd = cost_original / mep_rate if p.asset_type == 'ar' else cost_original
    
    # P&L
    pnl_usd = val_usd - cost_usd
    
    total_usd += val_usd
    total_pnl_usd += pnl_usd
    total_cost_usd += cost_usd
    
    if p.change_pct > best_change:
        best_change = p.change_pct
        best_performer = p

total_pnl_pct = (total_pnl_usd / total_cost_usd * 100) if total_cost_usd > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Valor Total (USD)", f"${total_usd:,.2f}")
with col2:
    st.metric("📈 Ganancia Total", f"${total_pnl_usd:,.2f}", f"{total_pnl_pct:+.2f}%")
with col3:
    st.metric("📦 Posiciones", len(portfolio.positions))
with col4:
    if best_performer:
        st.metric("🏆 Mejor Activo Hoy", best_performer.ticker, f"{best_performer.change_pct:+.2f}%")
    else:
        st.metric("🏆 Mejor Activo Hoy", "—")

st.divider()

# ───────── GRÁFICOS ─────────
chart_col1, chart_col2 = st.columns(2)

# 1. Gráfico de Distribución (Donut)
with chart_col1:
    st.subheader("🥧 Distribución del Portfolio")
    if portfolio.positions:
        data_pie = []
        for p in portfolio.positions:
            val_usd = p.current_value_original / mep_rate if p.asset_type == 'ar' else p.current_value_original
            data_pie.append({"Activo": p.ticker, "Valor USD": val_usd})
        
        df_pie = pd.DataFrame(data_pie)
        fig_pie = px.pie(df_pie, values="Valor USD", names="Activo", hole=0.7)
        fig_pie.update_traces(textinfo='percent+label', textposition='outside')
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Agregá posiciones para ver la distribución.")

# 2. Gráfico Histórico (Línea)
with chart_col2:
    st.subheader("📈 Histórico vs Benchmark")
    history = snapshot_service.get_history(days=30) # Por defecto 1M
    
    if history and len(history) >= 2:
        df_hist = pd.DataFrame(history)
        # ✅ CORRECCIÓN CRÍTICA: Asegurar que 'date' sea datetime para Plotly
        df_hist['date'] = pd.to_datetime(df_hist['date'])
        
        fig_line = px.line(
            df_hist, 
            x='date', 
            y=['totalUSD', 'benchmark'],
            labels={'value': 'USD', 'variable': ''},
            color_discrete_map={'totalUSD': '#378ADD', 'benchmark': '#1D9E75'}
        )
        fig_line.update_layout(
            margin=dict(t=0, b=0, l=0, r=0), 
            height=400,
            hovermode="x unified",
            xaxis_tickformat='%d/%m'
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.caption("📊 Se necesitan datos de varios días para generar el histórico.")

# ───────── TABLA DE POSICIONES ─────────
st.subheader("📋 Detalle de Posiciones")

if portfolio.positions:
    table_data = []
    for p in portfolio.positions:
        # Cálculos seguros evitando atributos inexistentes
        current_val_orig = p.current_value_original
        cost_total_orig = p.avg_cost_original * p.total_qty if p.avg_cost_original else 0
        pnl_orig = current_val_orig - cost_total_orig
        
        # Conversión a USD para visualización
        divisor = mep_rate if p.asset_type == 'ar' else 1.0
        
        current_val_usd = current_val_orig / divisor
        pnl_usd = pnl_orig / divisor
        ppc_usd = (p.avg_cost_original / divisor) if p.avg_cost_original else 0
        current_price_usd = (p.current_price / divisor) if p.current_price else 0
        
        # PER (Profit/Performance)
        per = (pnl_orig / cost_total_orig * 100) if cost_total_orig > 0.01 else 0
        
        table_data.append({
            "Ticker": p.ticker,
            "Tipo": p.asset_type.upper(),
            "Cantidad": format_qty(p.total_qty),
            "PPC (USD)": f"${ppc_usd:,.2f}",
            "Precio Actual": f"${current_price_usd:,.2f}",
            "Variación": f"{p.change_pct:+.2f}%",
            "Valor (USD)": f"${current_val_usd:,.2f}",
            "P&L (USD)": f"${pnl_usd:,.2f}",
            "PER %": f"{per:+.2f}%"
        })
        
    df_table = pd.DataFrame(table_data)
    
    # Estilizado condicional
    def color_negative_red(val):
        if isinstance(val, str):
            if val.startswith('-') or '−' in val:
                return 'color: #f87171' # Rojo para pérdidas
            elif val.startswith('+'):
                return 'color: #4ade80' # Verde para ganancias
        return ''

    styled_table = df_table.style.map(color_negative_red, subset=['Variación', 'P&L (USD)', 'PER %'])
    st.dataframe(styled_table, use_container_width=True, hide_index=True)
else:
    st.info("📭 No tenés posiciones activas. Usá el sidebar para agregar tu primera posición.")

# ───────── FOOTER: EXPORTAR / IMPORTAR ─────────
st.divider()
col_exp, col_imp = st.columns(2)

with col_exp:
    if st.button("📥 Exportar Backup JSON", use_container_width=True):
        export_data = []
        for p in portfolio.positions:
            holdings_list = []
            for h in p.holdings:
                holdings_list.append({
                    'qty': h.qty,
                    'price': h.price,
                    'date': h.date.isoformat(),
                    'tc': h.tc
                })
            export_data.append({
                'ticker': p.ticker,
                'asset_type': p.asset_type,
                'holdings': holdings_list
            })
        
        # Agregar histórico al backup
        full_backup = {
            "positions": export_data,
            "history": snapshot_service.history,
            "exported_at": datetime.now().isoformat()
        }
        
        json_str = json.dumps(full_backup, indent=2, ensure_ascii=False)
        st.download_button(
            label="⬇️ Descargar Archivo",
            data=json_str,
            file_name=f"amygdale_backup_{datetime.now().date()}.json",
            mime="application/json",
            use_container_width=True
        )

with col_imp:
    uploaded_file = st.file_uploader(
        "📤 Importar Backup", 
        type=["json"], 
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode("utf-8")
            data = json.loads(content)
            
            if "positions" in data:
                # Limpiar estado actual
                st.session_state.portfolio = Portfolio()
                portfolio = st.session_state.portfolio
                
                for pos_dict in data["positions"]:
                    for h in pos_dict.get('holdings', []):
                        portfolio.add_position(
                            ticker=pos_dict.get('ticker'),
                            asset_type=pos_dict.get('asset_type'),
                            qty=float(h.get('qty', 0)),
                            ppc=float(h.get('price', 0)),
                            tc=float(h.get('tc')) if h.get('tc') else None
                        )
                
                # Guardar importación
                storage.save_positions(data["positions"])
                
                # Importar histórico si existe
                if "history" in data and isinstance(data["history"], list):
                    snapshot_service.history = data["history"]
                    snapshot_service._save_history()
                
                st.success("✅ Portfolio importado correctamente.")
                st.rerun()
            else:
                st.error("❌ Formato de archivo inválido.")
                
        except Exception as e:
            st.error(f"❌ Error al importar: {str(e)}")

# ───────── GUARDAR SNAPSHOT DIARIO ─────────
# Se ejecuta al final para registrar el valor del día si es necesario
snapshot_service.save_snapshot(total_usd, mep_rate)