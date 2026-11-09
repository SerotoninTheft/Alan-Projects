
import tkinter as tk
from tkinter import ttk
import math

# Gas properties: R (J/kg K), cp (J/kg K)
gases = {
    "Air": (287.0, 1005.0),
    "Nitrogen": (296.8, 1040.0),
    "Oxygen": (259.8, 918.0),
    "Hydrogen": (4124.0, 14300.0),
    "Helium": (2077.0, 5193.0),
    "Carbon Dioxide": (188.9, 844.0)
}

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
            text="No physical positive-temperature solution."
        )
        draw_cone(A1, A2, V1, 0, q)
        return

    T2 = (-2*c) / (b + math.sqrt(discriminant))

    if T2 <= 0:
        result.config(
            text="No physical positive-temperature solution."
        )
        draw_cone(A1, A2, V1, 0, q)
        return

    rho2 = P2 / (R * T2)
    V2 = mdot / (rho2 * A2)


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

    draw_cone(A1, A2, V1, V2, q, T1, T2)



def temp_to_color(temp):
    # Temperature in Celsius
    # Blue at 0°C, purple at 250°C, red at 500°C
    t = max(0, min(1, temp / 500))

    red = int(255 * t)
    green = 30
    blue = int(255 * (1 - t))

    return f"#{red:02x}{green:02x}{blue:02x}"



def draw_cone(A1, A2, V1, V2, q, T1, T2):
    canvas.delete("all")

    width = 620
    cy = 260
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
            outline=color
        )

    # Cone outline
    canvas.create_polygon(
        x1, cy-r1,
        x2, cy-r2,
        x2, cy+r2,
        x1, cy+r1,
        fill="",
        outline="black",
        width=2
    )

    # Opening outlines
    canvas.create_line(
        x1, cy-r1, x1, cy+r1,
        fill="black", width=3
    )

    canvas.create_line(
        x2, cy-r2, x2, cy+r2,
        fill="black", width=3
    )


    # Flow arrow
    canvas.create_line(
        x1+30, cy,
        x2+60, cy,
        arrow=tk.LAST,
        fill="#e76f51",
        width=4
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
        justify="center"
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
        justify="center"
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
        310, 60,
        text=heat_text,
        font=("Arial", 14, "bold"),
        fill=heat_color
    )

    if heat_arrow:
        canvas.create_line(
            310, 90,
            310, 170,
            arrow=heat_arrow,
            fill=heat_color,
            width=4
        )

    canvas.create_text(
        310, 480,
        text="Single Stream Steady Flow System",
        font=("Arial", 14, "bold")
    )


# ---------------- GUI ----------------

root = tk.Tk()
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
    padx=15,
    pady=10
)

tk.Label(
    left_frame,
    text="STEADY FLOW CONTROLS",
    font=("Arial", 15, "bold")
).pack(pady=10)

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

canvas = tk.Canvas(
    right_frame,
    width=620,
    height=550,
    bg="white",
    highlightthickness=1,
    highlightbackground="gray"
)
canvas.pack(pady=20)

calculate()
root.mainloop()
