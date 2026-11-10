import random
import time

import tkinter as tk
from tkinter import ttk
import math


# GUI color palette
BG_COLOR = "#DDDDDD"       # Main background
TEXT_COLOR = "#222222"     # All text




mainMenu = True
gameMode = 0
# 1 = free-play, 2 = mission mode, 3 = comparison mode




score = 0
current_mission = None
mission_complete = False

MISSION_TEMP_TOL = 5       # °C
MISSION_VELOCITY_TOL = 5  # m/s
MISSION_INPUT_TOL = 5.0
MISSION_AREA_TOL = 0.05  # ±0.01 m²


# Gas properties: R (J/kg K), cp (J/kg K)
gases = {
    "Air": (287.0, 1005.0),
    "Nitrogen": (296.8, 1040.0),
    "Oxygen": (259.8, 918.0),
    "Hydrogen": (4124.0, 14300.0),
    "Helium": (2077.0, 5193.0),
    "Carbon Dioxide": (188.9, 844.0)
}
# Approximate reference properties:
# critical temperature (K), critical pressure (kPa),
# triple-point temperature (K), triple-point pressure (kPa),
# normal boiling point (K), normal melting point (K)

gas_reference = {
    "Air": (132.5, 3786, 59.8, 5.3, 78.8, 59.0),
    "Nitrogen": (126.2, 3396, 63.15, 12.5, 77.36, 63.15),
    "Oxygen": (154.6, 5043, 54.36, 0.146, 90.19, 54.36),
    "Hydrogen": (33.15, 1296, 13.8, 7.04, 20.28, 14.0),
    "Helium": (5.20, 227, 2.18, 5.0, 4.22, None),
    "Carbon Dioxide": (304.13, 7377, 216.59, 517.95, 194.65, 216.59)
}

k_B = 1.380649e-23

# Molecules represented by one animated dot
MOLECULES_PER_DOT = 1e25

def randomize_inputs():
    sliders = [
        temp_slider,
        pressure_slider,
        speed_slider,
        area_slider,
        out_pressure_slider,
        out_area_slider,
        heat_slider
    ]

    for slider in sliders:
        minimum = float(slider.cget("from"))
        maximum = float(slider.cget("to"))
        resolution = float(slider.cget("resolution"))

        steps = round((maximum - minimum) / resolution)
        value = minimum + random.randint(0, steps) * resolution

        slider.set(value)

    gas_choice.set(random.choice(list(gases.keys())))
    calculate()


def display_mission():
    if current_mission is None:
        return

    m = current_mission
    tolerance = MISSION_INPUT_TOL

    if m["fixed_name"] in ("Inlet area", "Outlet area"):
        tolerance = MISSION_AREA_TOL
    mission_label.config(
        text=(
            f"Gas: {m['gas']}\n"
            f"Reach outlet temperature: "
            f"{m['temperature']:.1f} °C "
            f"(±{MISSION_TEMP_TOL:g} °C)\n"
            f"Reach outlet velocity: "
            f"{m['velocity']:.1f} m/s "
            f"(±{MISSION_VELOCITY_TOL:g} m/s)\n"
            f"Keep {m['fixed_name']} at "
            f"{m['fixed_value']:.2f} "
            f"(±{tolerance:g})\n\n"
            f"Move input sliders to achieve the requirements without warnings to score!"
        )
    )

    score_label.config(text=f"Score: {score}")

def check_mission(T2, V2, warnings):
    global score

    if gameMode != 2 or current_mission is None:
        return

    if warnings:
        return

    m = current_mission

    correct_gas = gas_choice.get() == m["gas"]

    correct_temp = (
        abs((T2 - 273.15) - m["temperature"])
        <= MISSION_TEMP_TOL
    )

    correct_velocity = (
        abs(V2 - m["velocity"])
        <= MISSION_VELOCITY_TOL
    )
    
    slider = mission_sliders[m["fixed_name"]]
    resolution = float(slider.cget("resolution"))

    tolerance = MISSION_INPUT_TOL

    if m["fixed_name"] in ("Inlet area", "Outlet area"):
        tolerance = MISSION_AREA_TOL

    correct_fixed = (
        abs(slider.get() - m["fixed_value"])
        <= max(tolerance, resolution / 2)
    )

    if not all((
        correct_gas,
        correct_temp,
        correct_velocity,
        correct_fixed
    )):
        return
    score += 1

    mission_status.config(
        text=f"🎉 Mission complete! Score: {score}"
    )

    generate_mission()


def show_error(message):
    canvas.delete("cone")
    canvas.delete("particle")
    canvas.delete("error")

    particles.clear()

    canvas.create_text(
        310, 220,
        text=message,
        fill="red",
        font=("Arial", 16, "bold"),
        justify="center",
        width=500,
        tags="error"
    )

def update_warnings(warnings):
    if not warnings:
        warning_label.config(
            text="✓ No realism warnings detected.",
            fg="green"
        )
        return

    message = "\n\n".join(
        f"⚠ {warning}" for warning in warnings
    )

    warning_label.config(
        text=message,
        fg="#b45309"
    )


def generate_mission():
    global current_mission

    sliders = {
        "T1": temp_slider,
        "P1": pressure_slider,
        "V1": speed_slider,
        "A1": area_slider,
        "P2": out_pressure_slider,
        "A2": out_area_slider,
        "q": heat_slider
    }

    for attempt in range(2000):
        gas = random.choice(list(gases))
        values = {
            key: random_slider_value(slider)
            for key, slider in sliders.items()
        }

        state = mission_physics(
            gas,
            values["T1"], values["P1"],
            values["V1"], values["A1"],
            values["P2"], values["A2"],
            values["q"]
        )

        if state is None:
            continue

        T1, P1, V1, T2, P2, V2, A1, A2 = state
        if V2 > 120:
            continue
        if check_realism(gas, T1, P1, V1, T2, P2, V2, A1, A2):
            continue

        # Avoid generating a mission already solved by current settings.
        current_T2 = None
        if gas_choice.get() == gas:
            current_state = mission_physics(
                gas,
                temp_slider.get(),
                pressure_slider.get(),
                speed_slider.get(),
                area_slider.get(),
                out_pressure_slider.get(),
                out_area_slider.get(),
                heat_slider.get()
            )
            if current_state is not None:
                current_T2 = current_state[3] - 273.15

        if current_T2 is not None:
            same_temp = abs(current_T2 - (T2 - 273.15)) <= MISSION_TEMP_TOL
            same_velocity = abs(
                current_state[5] - V2
            ) <= MISSION_VELOCITY_TOL

            if same_temp and same_velocity:
                continue

        fixed_name = random.choice(list(mission_sliders))
        fixed_slider = mission_sliders[fixed_name]

        fixed_key = next(
            key for key, slider in sliders.items()
            if slider is fixed_slider
        )

        current_mission = {
            "gas": gas,
            "temperature": T2 - 273.15,
            "velocity": V2,
            "fixed_name": fixed_name,
            "fixed_key": fixed_key,
            "fixed_value": values[fixed_key],
            "solution": values
        }

        display_mission()
        return

    current_mission = None
    mission_label.config(
        text="Could not generate a warning-free mission.\nTry expanding the slider ranges."
    )

def mission_physics(gas, T1_C, P1_kPa, V1, A1, P2_kPa, A2, q_kJ):
    R, cp = gases[gas]

    T1 = T1_C + 273.15
    P1 = P1_kPa * 1000
    P2 = P2_kPa * 1000
    q = q_kJ * 1000

    if min(T1, P1, P2, A1, A2) <= 0 or V1 <= 0:
        return None

    rho1 = P1 / (R * T1)
    mdot = rho1 * A1 * V1

    k = mdot * R / (P2 * A2)
    a = 0.5 * k**2
    b = cp
    c = -cp*T1 - 0.5*V1**2 - q

    discriminant = b*b - 4*a*c

    if discriminant < 0:
        return None

    T2 = (-2*c) / (b + math.sqrt(discriminant))

    if T2 <= 0:
        return None

    rho2 = P2 / (R*T2)
    V2 = mdot / (rho2*A2)

    return T1, P1, V1, T2, P2, V2, A1, A2


def random_slider_value(slider):
    minimum = float(slider.cget("from"))
    maximum = float(slider.cget("to"))
    step = float(slider.cget("resolution"))

    steps = int((maximum - minimum) / step)
    return round(minimum + random.randint(0, steps) * step, 6)




def check_realism(gas, T1, P1, V1, T2, P2, V2, A1, A2):
    warnings = []

    R, cp = gases[gas]
    Tc, Pc, Tt, Pt, Tb, Tm = gas_reference[gas]

    # 1. Phase-change screening
    for name, T, P in [("Inlet", T1, P1), ("Outlet", T2, P2)]:
        if T <= 0:
            warnings.append(f"{name}: Invalid absolute temperature.")
            continue

        # Approximate saturation curve for pure gases
        if gas == "Air":
            if T < 90:
                warnings.append(
                    f"{name}: Air may partially condense or freeze. "
                    "Mixture phase behavior is not modeled."
                )

        elif gas == "Helium":
            if T < Tc and P < Pc:
                warnings.append(
                    f"{name}: Helium may be in a liquid-vapor region. "
                    "A helium-specific phase model is needed."
                )

        elif T < Tt:
            warnings.append(
                f"{name}: Temperature is below the triple point. "
                "Solid formation or sublimation may be relevant."
            )

        elif T < Tc:
            # Estimate saturation pressure using a fitted
            # Clausius-Clapeyron relation between triple
            # and critical reference points.
            slope = (
                math.log(Pc / Pt) /
                (1 / Tt - 1 / Tc)
            )

            Psat = Pt * math.exp(
                slope * (1 / Tt - 1 / T)
            )

            if P > Psat:
                warnings.append(
                    f"{name}: Possible condensation. "
                    f"P = {P/1000:.1f} kPa, "
                    f"estimated Psat = {Psat/1000:.1f} kPa."
                )

    # 2. Mach number
    gamma = cp / (cp - R)

    a1 = math.sqrt(gamma * R * T1)
    a2 = math.sqrt(gamma * R * T2)

    M1 = abs(V1) / a1
    M2 = abs(V2) / a2

    for name, M in [("Inlet", M1), ("Outlet", M2)]:
        if M >= 1:
            warnings.append(
                f"{name}: Sonic/supersonic flow "
                f"(Mach {M:.2f}). Choking may occur."
            )
        elif M >= 0.8:
            warnings.append(
                f"{name}: High subsonic flow "
                f"(Mach {M:.2f}). Compressibility is important."
            )

    # 3. Ideal-gas approximation
    for name, T, P in [("Inlet", T1, P1), ("Outlet", T2, P2)]:
        Tr = T / Tc
        Pr = P / (Pc * 1000)

        if Tr < 1.2 and Pr > 0.1:
            warnings.append(
                f"{name}: Near critical conditions "
                f"(Tr={Tr:.2f}, Pr={Pr:.2f}). "
                "Ideal-gas behavior may be inaccurate."
            )
        elif Pr > 0.5:
            warnings.append(
                f"{name}: Elevated reduced pressure "
                f"(Pr={Pr:.2f}). Consider real-gas properties."
            )

    # 4. Diffuser flow separation
    if A2 > A1:
        r1 = math.sqrt(A1 / math.pi)
        r2 = math.sqrt(A2 / math.pi)

        # Assumed physical cone length (meters)
        cone_length = 1.0

        half_angle = math.degrees(
            math.atan((r2 - r1) / cone_length)
        )

        if half_angle > 7:
            warnings.append(
                f"Diffuser: Expansion half-angle "
                f"{half_angle:.1f}°. Flow separation risk "
                "may be elevated."
            )

    return warnings

def calculate(value=None):
    R, cp = gases[gas_choice.get()]

    # Inlet conditions
    T1 = temp_slider.get() + 273.15
    P1 = pressure_slider.get() * 1000
    V1 = speed_slider.get()
    A1 = area_slider.get()

    # Outlet settings
    P2 = out_pressure_slider.get() * 1000
    A2 = out_area_slider.get()

    # Heat added or removed (kJ/kg)
    q = heat_slider.get() * 1000

    # Inlet density and mass flow
    rho1 = P1 / (R * T1)
    mdot = rho1 * A1 * V1

    # Molecular number density (molecules/m³)
    n1 = P1 / (k_B * T1)

    # Number of molecules entering per second
    molecules_per_second = n1 * A1 * V1

    # Convert molecular flow into visible dots per second
    dots_per_second = molecules_per_second / MOLECULES_PER_DOT

    # Continuity and energy equation:
    # V2 = mdot * R * T2 / (P2 * A2)
    # cp*(T2-T1) + (V2²-V1²)/2 = q

    k = mdot * R / (P2 * A2)
    a = 0.5 * k**2
    b = cp
    c = -cp*T1 - 0.5*V1**2 - q

    # Solve quadratic for actual outlet temperature
    discriminant = b**2 - 4*a*c

    if discriminant < 0:
        result.config(
            text="Invalid conditions: No real outlet temperature solution."
        )
        
        show_error("INVALID FLOW CONDITIONS\nNo real outlet temperature solution.")

        flow_state["V1"] = 0
        flow_state["V2"] = 0

        canvas.delete("particle")
        particles.clear()
        canvas.delete("cone")
        update_warnings([
            "Cannot evaluate realism: invalid outlet state."
        ])
        return

    T2 = (-2*c) / (b + math.sqrt(discriminant))

    if T2 <= 0:
        result.config(
            text="Invalid conditions: Outlet temperature below absolute zero."
        )

        show_error("INVALID FLOW CONDITIONS\nOutlet temperature below absolute zero.")

        flow_state["V1"] = 0
        flow_state["V2"] = 0

        canvas.delete("particle")
        particles.clear()
        canvas.delete("cone")
        update_warnings([
            "Cannot evaluate realism: invalid outlet state."
        ])
        return

    rho2 = P2 / (R * T2)
    V2 = mdot / (rho2 * A2)
    n2 = P2 / (k_B * T2)

    warnings = check_realism(
        gas_choice.get(),
        T1, P1, V1,
        T2, P2, V2,
        A1, A2
    )

    update_warnings(warnings)
    if gameMode == 2:
        check_mission(T2, V2, warnings)
    result.config(text=(
        f"Gas: {gas_choice.get()}\n"
        f"Mass Flow: {mdot:.3f} kg/s\n"
        f"Inlet Density: {rho1:.3f} kg/m³\n"
        f"Outlet Density: {rho2:.3f} kg/m³\n\n"
        f"Outlet Temp: {T2-273.15:.2f} °C\n"
        f"Outlet Velocity: {V2:.2f} m/s\n\n"
        f"Applied Heat: {q/1000:.2f} kJ/kg\n"
        f"Total Heat Rate: {mdot*q/1000:.2f} kW"
    ))

    flow_state.update({
        "A1": A1,
        "A2": A2,
        "V1": V1,
        "V2": V2,
        "dots_per_second": dots_per_second
    })

    draw_cone(A1, A2, V1, V2, q, T1, T2)



def temp_to_color(temp):
    # Temperature in Celsius
    # Blue at 0°C, purple at 250°C, red at 500°C
    t = max(0, min(1, temp / 500))

    red = int(255 * t)
    green = 30
    blue = int(255 * (1 - t))

    return f"#{red:02x}{green:02x}{blue:02x}"


# Particle animation settings
particles = []
particle_limit = 5000
spawn_rate = 2.5
spawn_accumulator = 0
last_frame = time.perf_counter()

# Current flow conditions
flow_state = {
    "A1": 0.1,
    "A2": 0.05,
    "V1": 20,
    "V2": 80
}

def visual_speed(v):
    # Nonlinear compression of real velocity
    # Keeps slow flow visible and fast flow manageable
    return 35 +v


def update_particles():
    global last_frame, spawn_accumulator

    now = time.perf_counter()
    dt = min(now - last_frame, 0.05)
    last_frame = now

    A1 = flow_state["A1"]
    A2 = flow_state["A2"]
    V1 = flow_state["V1"]
    V2 = flow_state["V2"]

    x1, x2 = 100, 520
    cy = 200

    r1 = max(12, math.sqrt(A1 / math.pi) * 180)
    r2 = max(12, math.sqrt(A2 / math.pi) * 180)

    # Spawn rate proportional to molecular flow
    spawn_accumulator += flow_state["dots_per_second"] * dt

    while spawn_accumulator >= 1 and len(particles) < particle_limit:
        offset = random.uniform(-0.95, 0.95)
        xoffset = random.uniform(-10, 10)

        
        particle_id = canvas.create_oval(
            0, 0, 0, 0,
            fill="#DDDDDD",
            outline="",
            tags="particle"
        )

        particles.append({
            "id": particle_id,
            "x": x1+xoffset,
            "offset": offset
        })

        spawn_accumulator -= 1

    # Move existing particles
    for p in particles[:]:
        fraction = (p["x"] - x1) / (x2 - x1)
        fraction = max(0, min(1, fraction))

        # Smooth velocity interpolation
        smooth = fraction * fraction * (3 - 2 * fraction)
        velocity = V1 + (V2 - V1) * smooth

        # visual speed
        speed = visual_speed(velocity)

        p["x"] += speed * dt

        fraction = (p["x"] - x1) / (x2 - x1)

        if fraction >= 1:
            canvas.delete(p["id"])
            particles.remove(p)
            continue

        # Cone radius at current x
        radius = r1 + (r2 - r1) * fraction

        # Keep particle within cone
        y = cy + p["offset"] * radius

        size = 2.5

        canvas.coords(
            p["id"],
            p["x"] - size,
            y - size,
            p["x"] + size,
            y + size
        )

    # Keep particles above the gradient
    canvas.tag_raise("particle")
    canvas.tag_raise("error")
    canvas.after(16, update_particles)



def draw_cone(A1, A2, V1, V2, q, T1, T2):
    canvas.delete("cone")
    canvas.delete("error")

    
    width = 620
    cy = 200
    x1 = 100
    x2 = 520

    # Radius proportional to sqrt(area)
    r1 = math.sqrt(A1 / math.pi) * 180
    r2 = math.sqrt(A2 / math.pi) * 180

    # Scale up for visibility
    r1 = max(12, r1)
    r2 = max(12, r2)



    # Temperature colors
    color1 = temp_to_color(T1 - 273.15)
    color2 = temp_to_color(T2 - 273.15)

    # Convert hex colors to RGB
    rgb1 = [int(color1[i:i+2], 16) for i in (1, 3, 5)]
    rgb2 = [int(color2[i:i+2], 16) for i in (1, 3, 5)]

    # Draw cone as thin colored strips
    steps = 150

    for i in range(steps):
        fraction1 = i / steps
        fraction2 = (i + 1) / steps

        xa = x1 + (x2 - x1) * fraction1
        xb = x1 + (x2 - x1) * fraction2

        ra = r1 + (r2 - r1) * fraction1
        rb = r1 + (r2 - r1) * fraction2

        rgb = [
            int(rgb1[j] + (rgb2[j] - rgb1[j]) * fraction1)
            for j in range(3)
        ]

        color = "#{:02x}{:02x}{:02x}".format(*rgb)

        canvas.create_polygon(
            xa, cy-ra,
            xb+1, cy-rb,
            xb+1, cy+rb,
            xa, cy+ra,
            fill=color,
            outline=color,
            tags="cone"
        )

    # Cone outline
    canvas.create_polygon(
        x1, cy-r1,
        x2, cy-r2,
        x2, cy+r2,
        x1, cy+r1,
        fill="",
        outline="black",
        width=2,
        tags="cone"
    )



    # Inlet label
    canvas.create_text(
        x1, cy+r1+45,
        text=(
            f"INLET\n"
            f"T = {T1-273.15:.1f} °C\n"
            f"A = {A1:.3f} m²\n"
            f"V = {V1:.1f} m/s"
        ),
        font=("Arial", 11),
        justify="center",
        fill = TEXT_COLOR,
        tags="cone"

    )

    # Outlet label
    canvas.create_text(
        x2, cy+r2+45,
        text=(
            f"OUTLET\n"
            f"T = {T2-273.15:.1f} °C\n"
            f"A = {A2:.3f} m²\n"
            f"V = {V2:.1f} m/s"
        ),
        font=("Arial", 11),
        justify="center",
        fill = TEXT_COLOR,
        tags="cone"

    )

    # Heat transfer indication
    if q > 0:
        heat_text = f"HEATING: +{q/1000:.1f} kJ/kg"
        heat_color = "red"
        heat_arrow = tk.LAST
    elif q < 0:
        heat_text = f"COOLING: {q/1000:.1f} kJ/kg"
        heat_color = "blue"
        heat_arrow = tk.FIRST
    else:
        heat_text = "ADIABATIC: q = 0"
        heat_color = "gray"
        heat_arrow = None

    canvas.create_text(
        310, 30,
        text=heat_text,
        font=("Arial", 14, "bold"),
        fill=heat_color,
        tags="cone"
    )

    if heat_arrow:
        canvas.create_line(
            310, 60,
            310, 120,
            arrow=heat_arrow,
            fill=heat_color,
            width=4,
            tags="cone"
        )

    canvas.create_text(
        310, 400,
        text="Single Stream Steady Flow System",
        font=("Arial", 14, "bold"),
        fill=TEXT_COLOR,
        tags="cone"
    )


# ---------------- GUI ----------------

root = tk.Tk()
root.configure(bg=BG_COLOR)

root.option_add("*Background", BG_COLOR)
root.option_add("*Foreground", TEXT_COLOR)
root.option_add("*highlightBackground", BG_COLOR)

root.title("Steady Flow Simulator")
root.geometry("1100x850")

# Left panel
# Scrollable left panel
left_container = tk.Frame(root, width=440)
left_container.pack(side="left", fill="y", padx=10, pady=10)
left_container.pack_propagate(False)

scroll_canvas = tk.Canvas(left_container, highlightthickness=0)
scrollbar = ttk.Scrollbar(
    left_container,
    orient="vertical",
    command=scroll_canvas.yview
)

scroll_canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
scroll_canvas.pack(side="left", fill="both", expand=True)

# All existing sliders go inside this frame
left_frame = tk.Frame(scroll_canvas)

window_id = scroll_canvas.create_window(
    (0, 0),
    window=left_frame,
    anchor="nw"
)

def update_scroll_region(event):
    scroll_canvas.configure(
        scrollregion=scroll_canvas.bbox("all")
    )

def resize_content(event):
    scroll_canvas.itemconfigure(
        window_id,
        width=event.width
    )

left_frame.bind("<Configure>", update_scroll_region)
scroll_canvas.bind("<Configure>", resize_content)




# Right panel
right_frame = tk.Frame(root)
right_frame.pack(
    side="right",
    fill="both",
    expand=True,
    padx=20,
    pady=10
)

tk.Label(
    left_frame,
    text="STEADY FLOW CONTROLS",
    font=("Arial", 15, "bold")
).pack(pady=5)



randomize_button = tk.Button(
    left_frame,
    text="Randomize Inputs", padx=20, pady=10,
    command=randomize_inputs
)
randomize_button.pack(pady=15)



tk.Label(left_frame, text="Select Gas").pack()

gas_choice = ttk.Combobox(
    left_frame,
    values=list(gases.keys()),
    state="readonly"
)
gas_choice.set("Air")
gas_choice.pack(pady=5)
gas_choice.bind("<<ComboboxSelected>>", calculate)


def add_slider(label, minimum, maximum, default, resolution=1):
    tk.Label(left_frame, text=label).pack()

    slider = tk.Scale(
        left_frame,
        from_=minimum,
        to=maximum,
        resolution=resolution,
        orient="horizontal",
        length=350,
        command=calculate
    )
    slider.set(default)
    slider.pack(pady=1)
    return slider


tk.Label(
    left_frame,
    text="INLET",
    font=("Arial", 12, "bold")
).pack(pady=8)

temp_slider = add_slider(
    "Temperature (°C)", 0, 500, 25
)
pressure_slider = add_slider(
    "Pressure (kPa)", 50, 1000, 200
)
speed_slider = add_slider(
    "Velocity (m/s)", 0, 200, 20
)
area_slider = add_slider(
    "Area (m²)", 0.01, 1, 0.1, 0.01
)

tk.Label(
    left_frame,
    text="OUTLET",
    font=("Arial", 12, "bold")
).pack(pady=8)

out_pressure_slider = add_slider(
    "Pressure (kPa)", 10, 1000, 100
)
out_area_slider = add_slider(
    "Area (m²)", 0.01, 1, 0.05, 0.01
)

tk.Label(
    left_frame,
    text="ENERGY TRANSFER",
    font=("Arial", 12, "bold")
).pack(pady=8)

heat_slider = add_slider(
    "Heat Transfer (kJ/kg)", -500, 500, 0
)

tk.Label(
    left_frame,
    text="CALCULATED RESULTS",
    font=("Arial", 12, "bold")
).pack(pady=10)

result = tk.Label(
    left_frame,
    text="",
    font=("Arial", 11),
    justify="left"
)
result.pack(pady=5)




tk.Label(
    right_frame,
    text="FLOW VISUALIZATION",
    font=("Arial", 16, "bold")
).pack(pady=10)



mission_sliders = {
    "Inlet temperature": temp_slider,
    "Inlet pressure": pressure_slider,
    "Inlet speed": speed_slider,
    "Inlet area": area_slider,
    "Outlet area": out_area_slider,
    "Heat input": heat_slider
}


# Physical realism warning panel
warning_frame = tk.LabelFrame(
    right_frame,
    text="Physical Realism Warnings",
    font=("Arial", 12, "bold"),
    padx=12,
    pady=10
)
warning_frame.pack(fill="x", padx=10, pady=10)

warning_label = tk.Label(
    warning_frame,
    text="Checking flow conditions...",
    font=("Arial", 10),
    justify="left",
    anchor="w",
    wraplength=550
)
warning_label.pack(fill="x")


canvas = tk.Canvas(
    right_frame,
    width=620,
    height=440,
    bg=BG_COLOR,
    highlightthickness=1,
    highlightbackground="gray"
)
canvas.pack(pady=20)


mission_frame = tk.LabelFrame(
    right_frame,
    text="Mission Mode",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    font=("Arial", 12, "bold"),
    padx=12,
    pady=10
)

score_label = tk.Label(
    mission_frame,
    text="Score: 0",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    font=("Arial", 13, "bold")
)
score_label.pack(anchor="w")

mission_label = tk.Label(
    mission_frame,
    text="",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    font=("Arial", 11),
    justify="left",
    wraplength=500
)
mission_label.pack(anchor="w", pady=8)

mission_status = tk.Label(
    mission_frame,
    text="",
    bg=BG_COLOR,
    fg="green",
    font=("Arial", 11, "bold")
)
mission_status.pack(anchor="w")


def freeplayon():
    global gameMode, mainMenu
    gameMode = 1
    mainMenu = False
    menuOverlay.place_forget()
def missionon():
    global gameMode, mainMenu


    gameMode = 2
    mission_frame.pack(fill="x", padx=10, pady=10)
    mission_status.config(text="")
    generate_mission()
    mainMenu = False
    menuOverlay.place_forget()
def comparisonon():
    global gameMode, mainMenu
    gameMode = 3
    mainMenu = False
    menuOverlay.place_forget()


    
if mainMenu:
    menuOverlay = tk.Frame(root, bg=BG_COLOR)
    #  place(relwidth=1, relheight=1) to stretch across 100% of parent width and height
    menuOverlay.place(relx=0, rely=0, relwidth=1, relheight=1.0)
    #  a message or widget on top of the overlay
    lbl = tk.Label(menuOverlay, text="Alan's Spectacular Steady\nState Steady Flow Systems", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 50, "bold"))
    lbl.pack(pady = 200)

    freePlayButton = tk.Button(menuOverlay, text="Free Play", padx=20, pady=10, command=freeplayon)
    freePlayButton.pack()
    missionButton = tk.Button(menuOverlay, text="Mission Mode", padx=20, pady=10, command=missionon)
    missionButton.pack()
    comparisonPlayButton = tk.Button(menuOverlay, text="Comparison Mode", padx=20, pady=10, command=comparisonon)
    comparisonPlayButton.pack()



calculate()
root.after(16, update_particles)
root.mainloop()
