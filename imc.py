
import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = "health_app.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS health_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            weight REAL,
            height REAL,
            imc REAL,
            cups INTEGER,
            note TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS exercise_log (
            id INTEGER PRIMARY KEY,
            entry_datetime TEXT,
            name TEXT,
            duration_min REAL,
            calories REAL,
            met REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS routine_items (
            id INTEGER PRIMARY KEY,
            routine_id INTEGER,
            exercise_name TEXT,
            sets INTEGER,
            reps INTEGER,
            duration_min REAL,
            FOREIGN KEY(routine_id) REFERENCES routines(id)
        )
    ''')
    conn.commit()
    conn.close()

def run_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.commit()
    conn.close()
    return rows

init_db()

COMMON_METS = {
    "corrida (8 km/h)": 9.8,
    "corrida (10 km/h)": 11.5,
    "caminhada (5 km/h)": 3.5,
    "bicicleta moderada": 7.5,
    "pular corda": 12.0,
    "flexões": 8.0,
    "agachamentos (rítmicos)": 5.0,
    "polichinelos": 8.0,
    "yoga": 3.0,
    "treino HIIT (intenso)": 12.0,
    "natação (moderada)": 8.0,
}

def calculate_imc(weight, height):
    if height <= 0:
        return None
    return weight / (height ** 2)

def imc_classification(imc):
    if imc is None:
        return "Altura inválida"
    if imc < 18.5:
        return "Baixo peso"
    elif 18.5 <= imc < 25:
        return "Peso normal"
    elif 25 <= imc < 30:
        return "Sobrepeso"
    elif 30 <= imc < 35:
        return "Obesidade grau I"
    elif 35 <= imc < 40:
        return "Obesidade grau II"
    else:
        return "Obesidade grau III"

def calories_burned(met, weight_kg, duration_min):
    return met * weight_kg * (duration_min / 60.0)

def save_health_entry(weight, height, cups, note):
    imc = calculate_imc(weight, height)
    run_query('''
        INSERT INTO health_entries (entry_date, weight, height, imc, cups, note)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date.today().isoformat(), weight, height, imc, cups, note))

def log_exercise(name, duration_min, calories, met):
    run_query('''
        INSERT INTO exercise_log (entry_datetime, name, duration_min, calories, met)
        VALUES (?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), name, duration_min, calories, met))

def create_routine(name, type_):
    run_query('''
        INSERT INTO routines (name, type, created_at) VALUES (?, ?, ?)
    ''', (name, type_, datetime.now().isoformat()))
    rows = run_query('SELECT id FROM routines ORDER BY id DESC LIMIT 1')
    return rows[0][0]

def add_routine_item(routine_id, exercise_name, sets, reps, duration_min):
    run_query('''
        INSERT INTO routine_items (routine_id, exercise_name, sets, reps, duration_min)
        VALUES (?, ?, ?, ?, ?)
    ''', (routine_id, exercise_name, sets, reps, duration_min))

st.set_page_config(page_title="Health & Fitness Hub", layout="wide")
st.title("Health & Fitness Hub ")
st.markdown("Aplicativo com IMC, hidratação, queima calórica, criação de treinos e acompanhamento de progresso.")

menu = st.sidebar.selectbox("Navegar", [
    "Dashboard",
    "Registrar Saúde (IMC & Água)",
    "Queima de Calorias (Exercício)",
    "Criar Treino",
    "Ver Treinos & Log",
    "Progresso e Gráficos"
])

if menu == "Dashboard":
    st.header("Resumo rápido de hoje")
    rows = run_query('SELECT entry_date, weight, height, imc, cups FROM health_entries ORDER BY id DESC LIMIT 1')
    if rows:
        entry_date, w, h, imc, cups = rows[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Peso (kg)", f"{w:.1f}" if w else "—")
        col2.metric("Altura (m)", f"{h:.2f}" if h else "—")
        col3.metric("IMC", f"{imc:.2f}" if imc else "—")
        col4.metric("Copos hoje", f"{cups} copos" if cups is not None else "—")
        if imc:
            st.write("Classificação:", imc_classification(imc))
    else:
        st.info("Nenhum registro de saúde ainda.")

    today = date.today().isoformat()
    logs = run_query('SELECT entry_datetime, name, duration_min, calories FROM exercise_log')
    df_logs = pd.DataFrame(logs, columns=["datetime", "name", "duration_min", "calories"]) if logs else pd.DataFrame()
    if not df_logs.empty:
        df_logs['date'] = pd.to_datetime(df_logs['datetime']).dt.date
        today_df = df_logs[df_logs['date'] == date.today()]
        total_cal = today_df['calories'].sum() if not today_df.empty else 0
        total_time = today_df['duration_min'].sum() if not today_df.empty else 0
        st.metric("Calorias queimadas hoje", f"{total_cal:.0f} kcal")
        st.metric("Tempo total de exercício hoje", f"{total_time:.0f} min")
    else:
        st.write("Nenhum exercício registrado ainda.")
    
    if not df_logs.empty:
        today_df = df_logs[df_logs['date'] == date.today()]
        if not today_df.empty:
            agg = today_df.groupby('name')['duration_min'].sum()
            fig, ax = plt.subplots(figsize=(6,6))
            wedges, texts = ax.pie(agg, wedgeprops=dict(width=0.35), startangle=90)
            ax.legend(wedges, agg.index, title="Exercícios", bbox_to_anchor=(1.1, 0.9))
            ax.set_title(f"Distribuição de tempo de exercícios hoje ({int(agg.sum())} min)")
            centre_circle = plt.Circle((0,0),0.70,fc='black')
            fig.gca().add_artist(centre_circle)
            st.pyplot(fig)

if menu == "Registrar Saúde (IMC & Água)":
    st.header("Registrar Saúde: Peso, Altura e Água ")
    with st.form("health_form"):
        weight = st.number_input("Peso (kg)", min_value=0.0, format="%.1f", value=70.0)
        height = st.number_input("Altura (m)", min_value=0.0, format="%.2f", value=1.75)
        cups = st.number_input("Quantos copos já tomou hoje? (200 mL por copo)", min_value=0, step=1, value=0)
        note = st.text_area("Observação (opcional)")
        submitted = st.form_submit_button("Salvar registro")
    if submitted:
        save_health_entry(weight, height, cups, note)
        st.success("Registro salvo!")
        imc = calculate_imc(weight, height)
        st.write(f"Seu IMC: **{imc:.2f}** — {imc_classification(imc)}")
        total_ml = cups * 200
        remaining_ml = max(2000 - total_ml, 0)
        st.write(f"Ingestão de hoje: **{total_ml} mL**. Falta **{remaining_ml} mL** para 2 L.")
        st.progress(min(total_ml/2000, 1.0))

if menu == "Queima de Calorias (Exercício)":
    st.header("Calcular calorias queimadas por exercício ")
    last = run_query('SELECT weight FROM health_entries ORDER BY id DESC LIMIT 1')
    default_weight = last[0][0] if last else 70.0

    weight = st.number_input("Seu peso (kg)", min_value=1.0, value=float(default_weight))
    exercise_name = st.text_input("Nome do exercício", "corrida (8 km/h)")
    duration_min = st.number_input("Duração (min)", min_value=1.0, value=30.0)
    met_choice = st.selectbox("Escolher MET sugerido", ["Auto (tenta sugerir)","Personalizado"] + list(COMMON_METS.keys()))
    met = None
    if met_choice == "Auto (tenta sugerir)":
        matched = None
        for k in COMMON_METS:
            if k.split()[0].lower() in exercise_name.lower():
                matched = COMMON_METS[k]
                break
        if matched:
            met = matched
            st.write(f"MET sugerido: {met:.1f}")
        else:
            st.warning("Não consegui sugerir um MET.")
    elif met_choice == "Personalizado":
        met = st.number_input("Informe o MET", min_value=0.1, value=8.0)
    else:
        met = COMMON_METS.get(met_choice, 8.0)

    if st.button("Calcular e registrar exercício"):
        calories = calories_burned(met, weight, duration_min)
        log_exercise(exercise_name, duration_min, calories, met)
        st.success(f"Exercício salvo: {exercise_name} — {duration_min:.0f} min — {calories:.0f} kcal")

if menu == "Criar Treino":
    st.header("Criar um treino (Rotina) ")
    with st.form("routine_form"):
        name = st.text_input("Nome do treino", "Treino Full Body")
        type_ = st.selectbox("Tipo", ["casa", "academia"])
        n_items = st.number_input("Quantos exercícios nesta rotina?", min_value=1, max_value=20, value=5, step=1)
        items = []
        for i in range(int(n_items)):
            st.markdown(f"**Exercício {i+1}**")
            ex_name = st.text_input(f"Nome {i+1}", value=f"Ex {i+1}", key=f"name_{i}")
            sets = st.number_input(f"Séries {i+1}", min_value=0, max_value=10, value=3, key=f"sets_{i}")
            reps = st.number_input(f"Repetições {i+1}", min_value=0, max_value=100, value=12, key=f"reps_{i}")
            duration = st.number_input(f"Duração (min) {i+1}", min_value=0.0, value=0.0, key=f"dur_{i}")
            items.append((ex_name, sets, reps, duration))
        submit_routine = st.form_submit_button("Criar e salvar rotina")
    if submit_routine:
        rid = create_routine(name, type_)
        for it in items:
            add_routine_item(rid, it[0], int(it[1]), int(it[2]), float(it[3]))
        st.success(f"Rotina '{name}' criada com sucesso!")

if menu == "Ver Treinos & Log":
    st.header("Treinos criados")
    routines = run_query('SELECT id, name, type, created_at FROM routines ORDER BY id DESC')
    if routines:
        for r in routines:
            r_id, r_name, r_type, created_at = r
            with st.expander(f"{r_name} — {r_type} — {created_at[:10]}"):
                items = run_query('SELECT exercise_name, sets, reps, duration_min FROM routine_items WHERE routine_id=?', (r_id,))
                st.table(pd.DataFrame(items, columns=["Exercício", "Séries", "Reps", "Duração (min)"]))
                if st.button(f"Marcar rotina '{r_name}' como feita agora", key=f"do_{r_id}"):
                    for it in items:
                        ename, sets, reps, dur = it
                        approx_dur = dur if dur and dur>0 else (sets * reps * 0.2)
                        last = run_query('SELECT weight FROM health_entries ORDER BY id DESC LIMIT 1')
                        weight = last[0][0] if last else 70.0
                        matched_met = None
                        for k,v in COMMON_METS.items():
                            if k.split()[0].lower() in ename.lower():
                                matched_met = v
                                break
                        met = matched_met if matched_met else 6.0
                        calories = calories_burned(met, weight, approx_dur)
                        log_exercise(ename, approx_dur, calories, met)
                    st.success("Rotina registrada no log de exercícios.")
    else:
        st.info("Nenhuma rotina criada ainda.")

    st.markdown("---")
    st.header("Log de exercícios")
    logs = run_query('SELECT id, entry_datetime, name, duration_min, calories FROM exercise_log ORDER BY id DESC LIMIT 200')
    if logs:
        df = pd.DataFrame(logs, columns=["id", "datetime", "name", "duration_min", "calories"])
        df['datetime'] = pd.to_datetime(df['datetime'])
        st.dataframe(df)
        if st.button("Limpar histórico de exercícios"):
            run_query('DELETE FROM exercise_log')
            st.warning("Histórico apagado. Recarregue a página.")
    else:
        st.write("Nenhum exercício registrado ainda.")

if menu == "Progresso e Gráficos":
    st.header("Progresso — evolução dos seus dados ")
    health = run_query('SELECT id, entry_date, weight, height, imc, cups FROM health_entries ORDER BY id')
    if health:
        df_h = pd.DataFrame(health, columns=["id","date","weight","height","imc","cups"])
        df_h['date'] = pd.to_datetime(df_h['date'])
        df_h = df_h.set_index('date')
        st.subheader("IMC ao longo do tempo")
        fig, ax = plt.subplots()
        ax.plot(df_h.index, df_h['imc'], marker='o')
        ax.set_ylabel("IMC")
        ax.set_xlabel("Data")
        ax.grid(alpha=0.3)
        st.pyplot(fig)

        st.subheader("Peso ao longo do tempo")
        fig2, ax2 = plt.subplots()
        ax2.plot(df_h.index, df_h['weight'], marker='o')
        ax2.set_ylabel("Peso (kg)")
        ax2.set_xlabel("Data")
        ax2.grid(alpha=0.3)
        st.pyplot(fig2)

        st.subheader("Ingestão de água (copos) — histórico")
        fig3, ax3 = plt.subplots()
        ax3.bar(df_h.index, df_h['cups'])
        ax3.set_ylabel("Copos (200 mL)")
        ax3.set_xlabel("Data")
        st.pyplot(fig3)
    else:
        st.info("Sem registros de saúde para mostrar gráficos.")

    logs = run_query('SELECT entry_datetime, name, duration_min, calories FROM exercise_log')
    if logs:
        df_logs = pd.DataFrame(logs, columns=["datetime","name","duration_min","calories"])
        df_logs['date'] = pd.to_datetime(df_logs['datetime']).dt.date
        st.subheader("Resumo de exercícios")
        agg = df_logs.groupby('name').agg({'duration_min':'sum','calories':'sum','datetime':'count'}).rename(columns={'datetime':'count'}).reset_index()
        st.dataframe(agg.sort_values('duration_min', ascending=False))

        fig4, ax4 = plt.subplots(figsize=(8,4))
        names = agg['name']
        ax4.barh(names, agg['duration_min'])
        ax4.set_xlabel("Tempo total (min)")
        ax4.set_ylabel("Exercício")
        st.pyplot(fig4)

        st.subheader("Onde você precisa praticar mais")
        agg['prop'] = agg['duration_min'] / (agg['duration_min'].max() if agg['duration_min'].max()>0 else 1)
        need = agg.sort_values('prop').head(5)
        for _, row in need.iterrows():
            st.write(f"- {row['name']}: tempo total {row['duration_min']:.0f} min ({row['count']} registros). Tente praticar mais este exercício.")
        
        top = agg.sort_values('duration_min', ascending=False).head(6)
        fig5, ax5 = plt.subplots(figsize=(5,5))
        values = top['duration_min']
        labels = top['name']
        wedges, texts = ax5.pie(values, wedgeprops=dict(width=0.35), startangle=90)
        ax5.legend(wedges, labels, title="Top exercícios", bbox_to_anchor=(1.1, 0.9))
        centre_circle = plt.Circle((0,0),0.70,fc='white')
        fig5.gca().add_artist(centre_circle)
        ax5.set_title("Distribuição de tempo entre principais exercícios")
        st.pyplot(fig5)

    else:
        st.info("Nenhum exercício registrado para gerar gráficos.")

    st.subheader("Últimos inputs do usuário")
    last_health = run_query('SELECT entry_date, weight, height, imc, cups FROM health_entries ORDER BY id DESC LIMIT 7')
    if last_health:
        df_last = pd.DataFrame(last_health, columns=["date","weight","height","imc","cups"])
        st.table(df_last)
    else:
        st.write("Nenhum dado salvo ainda.")
