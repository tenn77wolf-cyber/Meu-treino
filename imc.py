import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd

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
    "natação (moderada)": 8.0
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

    logs = run_query('SELECT entry_datetime, name, duration_min, calories FROM exercise_log')
    df_logs = pd.DataFrame(logs, columns=["datetime", "name", "duration_min", "calories"]) if logs else pd.DataFrame()
    if not df_logs.empty:
        df_logs['date'] = pd.to_datetime(df_logs['datetime']).dt.date
        today_df = df_logs[df_logs['date'] == date.today()]
        total_cal = today_df['calories'].sum() if not today_df.empty else 0
        total_time = today_df['duration_min'].sum() if not today_df.empty else 0
        st.metric("Calorias queimadas hoje", f"{total_cal:.0f} kcal")
        st.metric("Tempo total de exercício hoje", f"{total_time:.0f} min")

        agg = today_df.groupby('name')['duration_min'].sum().reset_index()
        st.subheader("Distribuição de tempo de exercícios hoje")
        st.dataframe(agg.rename(columns={'name':'Exercício', 'duration_min':'Tempo (min)'}))
    else:
        st.write("Nenhum exercício registrado ainda.")

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
        st.success(f"Exercício registrado! Você queimou aproximadamente {calories:.0f} kcal.")

if menu == "Criar Treino":
    st.header("Criar um novo treino")
    with st.form("workout_form"):
        workout_name = st.text_input("Nome do treino")
        workout_type = st.selectbox("Tipo de treino", ["Personalizado", "Cardio", "Força", "Flexibilidade"])
        workout_exercises = st.text_area("Exercícios (um por linha, formato: nome, séries, repetições, duração em min)")
        submitted = st.form_submit_button("Salvar treino")
    if submitted:
        if workout_name and workout_exercises:
            routine_id = create_routine(workout_name, workout_type)
            for line in workout_exercises.splitlines():
                parts = line.split(',')
                if len(parts) >= 4:
                    ex_name = parts[0].strip()
                    sets = int(parts[1].strip())
                    reps = int(parts[2].strip())
                    duration_min = float(parts[3].strip())
                    add_routine_item(routine_id, ex_name, sets, reps, duration_min)
            st.success("Treino salvo!")
        else:
            st.error("Por favor, preencha o nome do treino e os exercícios.")

if menu == "Ver Treinos & Log":
    st.header("Seus treinos salvos")
    routines = run_query('SELECT id, name, type, created_at FROM routines')
    if routines:
        for r in routines:
            rid, name, type_, created_at = r
            st.subheader(f"{name} ({type_})")
            st.write(f"Criado em: {created_at}")
            items = run_query('SELECT exercise_name, sets, reps, duration_min FROM routine_items WHERE routine_id=?', (rid,))
            if items:
                df_items = pd.DataFrame(items, columns=["Exercício", "Séries", "Repetições", "Duração (min)"])
                st.dataframe(df_items)
            else:
                st.write("Nenhum exercício adicionado.")
    else:
        st.write("Nenhum treino salvo ainda.")

    st.write("Log de exercícios:")
    log_items = run_query('SELECT entry_datetime, name, duration_min, calories FROM exercise_log ORDER BY entry_datetime DESC')
    if log_items:
        df_logs = pd.DataFrame(log_items, columns=["Data", "Exercício", "Duração (min)", "Calorias"])
        st.dataframe(df_logs)
    else:
        st.write("Nenhum exercício registrado ainda.")

if menu == "Progresso e Gráficos":
    st.header("Progresso e Gráficos")
    health_data = run_query('SELECT entry_date, weight, imc, cups FROM health_entries ORDER BY entry_date')
    if health_data:
        df_health = pd.DataFrame(health_data, columns=["Data", "Peso", "IMC", "Copos de Água"])
        st.subheader("Dados de Saúde")
        st.dataframe(df_health)

        st.subheader("Gráfico de Peso ao Longo do Tempo")
        df_health['Data'] = pd.to_datetime(df_health['Data'])
        st.line_chart(df_health.set_index('Data')['Peso'])

        st.subheader("Gráfico de IMC ao Longo do Tempo")
        st.line_chart(df_health.set_index('Data')['IMC'])

        st.subheader("Consumo de Água ao Longo do Tempo")
        st.bar_chart(df_health.set_index('Data')['Copos de Água'])
    else:
        st.write("Nenhum dado de saúde registrado ainda.")

    exercise_data = run_query('SELECT entry_datetime, name, duration_min, calories FROM exercise_log ORDER BY entry_datetime')
    if exercise_data:
        df_exercise = pd.DataFrame(exercise_data, columns=["Data", "Exercício", "Duração (min)", "Calorias"])
        df_exercise['Data'] = pd.to_datetime(df_exercise['Data'])
        st.subheader("Dados de Exercício")
        st.dataframe(df_exercise)

        st.subheader("Calorias Queimadas ao Longo do Tempo")
        cal_per_day = df_exercise.groupby(df_exercise['Data'].dt.date)['Calorias'].sum()
        st.bar_chart(cal_per_day)

        st.subheader("Duração Total de Exercícios ao Longo do Tempo")
        dur_per_day = df_exercise.groupby(df_exercise['Data'].dt.date)['Duração (min)'].sum()
        st.bar_chart(dur_per_day)
    else:
        st.write("Nenhum dado de exercício registrado ainda.")
