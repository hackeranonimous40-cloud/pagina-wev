from flask import Flask, jsonify, render_template, request, send_from_directory
import os
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'
app.config['IMAGES_FOLDER'] = ''

API_URL = "https://apiparagit-3yxs.onrender.com/precios"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/yeifer125/iadatos/main/historial2025.json"

cached_data = {"api": [], "github": [], "last_fetch": None}
CACHE_DURATION = timedelta(hours=1)

def fetch_api_data():
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [item for item in data if isinstance(item, dict) and "producto" in item]
    except Exception as e:
        print(f"Error fetching API: {e}")
    return []

def fetch_github_data():
    try:
        response = requests.get(GITHUB_RAW_URL, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching GitHub: {e}")
    return []

def should_refresh_cache():
    if cached_data["last_fetch"] is None:
        return True
    return datetime.now() - cached_data["last_fetch"] > CACHE_DURATION

def get_all_camote_data():
    if should_refresh_cache():
        cached_data["api"] = fetch_api_data()
        cached_data["github"] = fetch_github_data()
        cached_data["last_fetch"] = datetime.now()

    all_data = cached_data["github"] + cached_data["api"]
    camote_data = [item for item in all_data if item.get("producto", "").lower().find("camote") != -1]
    return camote_data

def parse_date(date_str):
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            pass
    return None

def analyze_camote_prices(camote_data):
    monthly_prices = defaultdict(list)

    for item in camote_data:
        fecha = item.get("fecha", "")
        promedio = item.get("promedio", "")

        if not fecha or not promedio:
            continue

        parsed_date = parse_date(fecha)
        if not parsed_date:
            continue

        try:
            avg_price = float(promedio)
            month_key = parsed_date.strftime("%Y-%m")
            monthly_prices[month_key].append(avg_price)
        except:
            continue

    monthly_avg = {}
    for month, prices in monthly_prices.items():
        if prices:
            monthly_avg[month] = statistics.mean(prices)

    return monthly_avg

def find_optimal_months(monthly_avg, harvest_months=3.5):
    if not monthly_avg:
        return []

    sorted_months = sorted(monthly_avg.items(), key=lambda x: x[1], reverse=True)

    if not sorted_months:
        return []

    avg_all = statistics.mean(list(monthly_avg.values()))
    optimal_planting = []

    for month_key, price in sorted_months:
        year, month = map(int, month_key.split("-"))
        plant_date = datetime(year, month, 1) - timedelta(days=int(harvest_months * 30))

        plant_month_num = plant_date.month
        plant_year = plant_date.year

        optimal_planting.append({
            "cosechar_mes": f"{get_month_name(month)} {year}",
            "cosechar_num": month,
            "plantar_mes": f"{get_month_name(plant_month_num)} {plant_year}",
            "plantar_num": plant_month_num,
            "plantar_year": plant_year,
            "precio_esperado": round(price, 2),
            "tipo": "excelente" if price > avg_all * 1.1 else "bueno" if price > avg_all else "normal",
            "dias_cultivo": int(harvest_months * 30)
        })

    return optimal_planting[:6]

def get_month_name(month_num):
    months = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    return months.get(month_num, "")

def get_all_planting_table(monthly_avg, harvest_months=3.5):
    if not monthly_avg:
        return []

    all_months = []
    avg_all = statistics.mean(list(monthly_avg.values()))

    for month_key, price in sorted(monthly_avg.items()):
        year, month = map(int, month_key.split("-"))
        plant_date = datetime(year, month, 1) - timedelta(days=int(harvest_months * 30))

        price_level = "alto" if price > avg_all * 1.2 else "medio" if price > avg_all * 0.9 else "bajo"

        all_months.append({
            "mes_cosecha": get_month_name(month),
            "mes_num": month,
            "year": year,
            "mes_plantar": get_month_name(plant_date.month),
            "plantar_num": plant_date.month,
            "plantar_year": plant_date.year,
            "precio": round(price, 2),
            "nivel_precio": price_level,
            "recomendacion": "OPTIMO" if price > avg_all * 1.1 else ("BUENO" if price > avg_all else "MENOR")
        })

    return all_months

@app.route("/")
@app.route("/index")
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read(), 200, {'Content-Type': 'text/html'}

@app.route("/camote")
def camote_page():
    return render_template("camote.html")

@app.route("/fotos/<path:filename>")
def serve_photos(filename):
    return send_from_directory("fotos", filename)

@app.route("/fondo.jpg")
def serve_fondo():
    return send_from_directory(".", "fondo.jpg")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(".", filename)

@app.route("/api/precios/camote")
def api_camote_prices():
    camote_data = get_all_camote_data()
    monthly = analyze_camote_prices(camote_data)
    return jsonify({
        "raw_data": camote_data,
        "monthly_average": monthly,
        "last_updated": datetime.now().isoformat()
    })

@app.route("/api/analisis/optimal")
def api_optimal_analysis():
    camote_data = get_all_camote_data()
    monthly = analyze_camote_prices(camote_data)
    optimal = find_optimal_months(monthly)

    return jsonify({
        "monthly_prices": monthly,
        "optimal_planting": optimal,
        "harvest_cycle_weeks": 3.5 * 4,
        "analysis_date": datetime.now().isoformat()
    })

@app.route("/api/precios/hoy")
def api_today_prices():
    camote_data = get_all_camote_data()

    today_prices = []
    for item in camote_data:
        fecha = item.get("fecha", "")
        if not fecha:
            continue
        parsed = parse_date(fecha)
        if parsed:
            today = datetime.now()
            if parsed.day == today.day and parsed.month == today.month:
                today_prices.append(item)

    if not today_prices:
        all_dates = {}
        for item in camote_data:
            fecha = item.get("fecha", "")
            if fecha:
                parsed = parse_date(fecha)
                if parsed:
                    key = parsed.strftime("%Y-%m-%d")
                    if key not in all_dates:
                        all_dates[key] = parsed

        if all_dates:
            latest_key = max(all_dates.keys())
            latest_date = all_dates[latest_key]
            for item in camote_data:
                fecha = item.get("fecha", "")
                if fecha:
                    parsed = parse_date(fecha)
                    if parsed and parsed.strftime("%Y-%m-%d") == latest_key:
                        item["fecha_mostrar"] = latest_date.strftime("%d/%m/%Y")
                        today_prices.append(item)

    return jsonify({
        "precios_hoy": today_prices,
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "total_encontrados": len(today_prices)
    })

@app.route("/api/tabla/siembra")
def api_planting_table():
    camote_data = get_all_camote_data()
    monthly = analyze_camote_prices(camote_data)
    table = get_all_planting_table(monthly)

    return jsonify({
        "tabla_completa": table,
        "ciclo_cultivo_dias": 105,
        "ciclo_cultivo_meses": 3.5,
        "tabla_headers": ["MES COSECHA", "MES PLANTAR", "PRECIO ₡", "RECOMENDACIÓN"],
        "generated_at": datetime.now().isoformat()
    })

@app.route("/api/calendario/siembra")
def api_planting_calendar():
    camote_data = get_all_camote_data()
    monthly = analyze_camote_prices(camote_data)
    optimal = find_optimal_months(monthly)

    calendar_data = []
    for i, opt in enumerate(optimal[:4]):
        calendar_data.append({
            "id": i + 1,
            "plantar": opt["plantar_mes"],
            "cosechar": opt["cosechar_mes"],
            "precio": opt["precio_esperado"],
            "nivel": opt["tipo"],
            "dias": opt["dias_cultivo"]
        })

    return jsonify({
        "calendar": calendar_data,
        "crop": "Camote",
        "growth_period_days": 105,
        "generated_at": current.isoformat()
    })

@app.route("/api/hermes/command", methods=["POST"])
def hermes_command():
    data = request.get_json()
    command = data.get("command", "").lower()

    response = {"status": "success", "message": "", "data": {}}

    if "actualizar" in command or "refresh" in command or "refrescar" in command:
        cached_data["last_fetch"] = None
        camote_data = get_all_camote_data()
        response["message"] = f"Datos actualizados. {len(camote_data)} registros de camote cargados."
        response["data"] = {"records": len(camote_data)}

    elif "precios" in command or "precio" in command:
        camote_data = get_all_camote_data()
        monthly = analyze_camote_prices(camote_data)
        response["message"] = "Precios de camote obtenidos"
        response["data"] = {"monthly": monthly, "total_records": len(camote_data)}

    elif "siembra" in command or "plantar" in command or "calendario" in command:
        camote_data = get_all_camote_data()
        monthly = analyze_camote_prices(camote_data)
        optimal = find_optimal_months(monthly)
        response["message"] = "Análisis de siembras óptimas"
        response["data"] = {"optimal_months": optimal}

    elif "mejor mes" in command or "mejor" in command:
        camote_data = get_all_camote_data()
        monthly = analyze_camote_prices(camote_data)
        if monthly:
            best = max(monthly.items(), key=lambda x: x[1])
            response["message"] = f"Mejor mes: {best[0]} con precio promedio de ₡{best[1]:.2f}"
            response["data"] = {"best_month": best[0], "best_price": best[1]}
        else:
            response["message"] = "No hay datos disponibles"
            response["status"] = "error"

    elif "cache" in command or "caché" in command:
        if "clear" in command or "limpiar" in command:
            cached_data["last_fetch"] = None
            response["message"] = "Cache limpiado. Datos se recargarán en la próxima solicitud."
        else:
            response["message"] = f"Cache último refresh: {cached_data['last_fetch']}"
            response["data"] = {"last_fetch": str(cached_data['last_fetch']) if cached_data['last_fetch'] else None}

    else:
        response["status"] = "unknown"
        response["message"] = "Comando no reconocido. Comandos disponibles: actualizar, precios, siembra, mejor mes, cache"

    return jsonify(response)

@app.route("/api/status")
def api_status():
    return jsonify({
        "api_url": API_URL,
        "github_url": GITHUB_RAW_URL,
        "cache_active": cached_data["last_fetch"] is not None,
        "last_fetch": str(cached_data["last_fetch"]) if cached_data["last_fetch"] else None,
        "endpoints": {
            "dashboard": "/",
            "camote_prices": "/api/precios/camote",
            "optimal_analysis": "/api/analisis/optimal",
            "planting_calendar": "/api/calendario/siembra",
            "hermes_commands": "/api/hermes/command",
            "status": "/api/status"
        }
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)