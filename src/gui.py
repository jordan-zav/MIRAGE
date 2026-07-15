import os
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import ColorInterp, Resampling
from skimage.draw import line as sk_line

from ai.parameter_advisor import recommend_settings
from pathlib import Path
from config import FEATURE_MODES, PARAM_INFO, PRESETS
from pipeline import run_extraction_job, validate_rgb_geotiff

AUTO_READ_MAX_DIM = 1400
THEME = {
    "bg": "#0f1825",
    "card": "#162235",
    "header_fg": "#9fd7d7",
    "sub_fg": "#7ba1bc",
    "section_fg": "#8fd2d2",
    "body_fg": "#dde8f2",
    "hint_fg": "#8ea4b6",
    "status_bg": "#1d3149",
    "status_fg": "#eef7ff",
    "accent": "#389898",
    "accent_hover": "#46acac",
    "link_fg": "#86d6d6",
}


UI_TEXT = {
    "en": {
        "header": "MIRAGE",
        "subtitle": (
            "MIRAGE rescues signatures, not generic lines. Choose Geological signature for "
            "natural/fractal directional patterns, or Archaeological signature for localized "
            "anthropogenic geometry."
        ),
        "lang_button": "Español",
        "ready": "Ready. Structural continuity profile is selected.",
        "data": "Data",
        "input": "Input GeoTIFF",
        "output": "Output folder",
        "browse": "Browse",
        "profile_section": "Detection Profile",
        "profile": "Profile",
        "apply": "Apply preset",
        "analyze": "Analyze raster and recommend",
        "mode_section": "Interpretation Goal",
        "mode": "Mode",
        "params": "Parameters",
        "run": "Run lineament extraction",
        "preview": "Preview lineaments",
        "hint": (
            "Recommendation: use Structural continuity for Geological signature and Geo-arch balance "
            "for Archaeological signature, then fine-tune thresholds from there."
        ),
        "priorities": "What This Run Prioritizes",
        "priorities_body": (
            "MIRAGE does not just trace generic lineaments. It rescues signatures according to the "
            "operator's interpretation goal.\n\n"
            "Geological signature favors preferred orientations linked to tectonic stress, with fractal "
            "and self-similar behavior under natural terrain noise.\n\n"
            "Archaeological signature preserves discrete anthropogenic geometry such as circles, "
            "rectilinear traces, and pipes, even with strong micro-relief disturbance."
        ),
        "tuning": "Tuning Notes",
        "tuning_body": (
            "If geological signatures are too noisy:\n"
            "Raise GTHR or LTHR.\n\n"
            "If archaeological figures are disappearing:\n"
            "Use Archaeological signature and lower LTHR a bit.\n\n"
            "If traces are too fragmented:\n"
            "Raise DTHR slightly."
        ),
        "confidence": "Recommendation Confidence",
        "about": "About",
        "license": "MIT License",
        "profile_loaded": "{profile} profile loaded.",
        "mode_selected": "{mode} mode selected.",
        "input_selected": "Input raster selected.",
        "output_selected": "Output folder selected.",
        "need_input_first": "Please select an input GeoTIFF first.",
        "need_input": "Please select an input GeoTIFF.",
        "need_output": "Please select an output folder.",
        "need_rgb": "MIRAGE accepts single-band, RGB GeoTIFF (3 bands), or RGBA with alpha as band 4.",
        "scores": "Scores",
        "metrics": "Metrics",
        "high": "High confidence",
        "moderate": "Moderate confidence",
        "low": "Low confidence",
        "best": "{confidence}. Best match: {top} (margin {margin} over {second}).",
        "analyzed": "Raster analyzed and recommendations applied.",
        "rec_title": "Raster recommendation",
        "rec_msg": (
            "Recommended profile: {profile}\n"
            "Recommended mode: {mode}\n"
            "Raster type: {family}\n\n"
            "Confidence: {confidence}\n"
            "Top-vs-next margin: {margin}\n\n"
            "Reason: {reason}\n\n"
            "The suggested parameters were applied, and you can still edit them manually."
        ),
        "auto_fail": "Auto-parameter estimation failed.",
        "auto_error": "Auto parameter error",
        "running": "Running extraction...",
        "ok": "Extraction completed successfully.",
        "done_title": "Finished",
        "done_msg": (
            "Lineament extraction completed successfully.\n\n"
            "Files were written to the selected output folder.\n\n"
            "Report:\n{report}"
        ),
        "preview_title": "Preview",
        "preview_ready": "Preview generated and opened.",
        "preview_missing": "Run extraction first so MIRAGE can preview lineaments.",
        "preview_fail": "Could not generate preview.",
        "fail": "Extraction failed.",
        "error": "Error",
        "no_raster": "No raster analyzed yet.",
        "analyze_prompt": "Analyze a raster to see the class scores and confidence.",
        "metric_contrast": "Contrast",
        "metric_edge_density": "Edge density",
        "metric_local_variance": "Local variance",
        "metric_circle": "Circle evidence",
        "metric_road": "Road evidence",
        "metric_lineation": "Lineation directionality",
        "metric_anomaly": "Anomaly salience",
        "geophys_filters_label": "Geophys Filters (TDR, AS, VDR1, VDR2, THDR)",
        "geophys_type_label": "Structure Type (trough / ridge)",
        "geophys_stride_label": "Curvature Stride (1=3x3, 2=5x5, 3=7x7)",
    },
    "es": {
        "header": "MIRAGE",
        "subtitle": (
            "MIRAGE rescata firmas, no líneas genéricas. Elige Firma geológica para patrones "
            "direccionales naturales/fractales, o Firma arqueológica para geometría antropogénica localizada."
        ),
        "lang_button": "English",
        "ready": "Listo. El perfil Structural continuity está seleccionado.",
        "data": "Datos",
        "input": "GeoTIFF de entrada",
        "output": "Carpeta de salida",
        "browse": "Examinar",
        "profile_section": "Perfil de Detección",
        "profile": "Perfil",
        "apply": "Aplicar preset",
        "analyze": "Analizar ráster y recomendar",
        "mode_section": "Objetivo Interpretativo",
        "mode": "Modo",
        "params": "Parámetros",
        "run": "Ejecutar extracción de lineamientos",
        "preview": "Vista previa de lineamientos",
        "hint": (
            "Recomendación: usa Structural continuity para Firma geológica y Geo-arch balance "
            "para Firma arqueológica, luego ajusta umbrales."
        ),
        "priorities": "Qué Prioriza Esta Corrida",
        "priorities_body": (
            "MIRAGE no solo traza lineamientos genéricos. Rescata firmas según el objetivo "
            "interpretativo del operador.\n\n"
            "Firma geológica favorece orientaciones preferenciales ligadas al esfuerzo tectónico, "
            "con comportamiento fractal y auto-similar bajo ruido natural del terreno.\n\n"
            "Firma arqueológica preserva geometría antropogénica discreta como círculos, "
            "trazas rectilíneas y pipes, incluso con fuerte perturbación de micro-relieve."
        ),
        "tuning": "Notas de Ajuste",
        "tuning_body": (
            "Si las firmas geológicas salen muy ruidosas:\n"
            "Sube GTHR o LTHR.\n\n"
            "Si las figuras arqueológicas desaparecen:\n"
            "Usa Firma arqueológica y baja un poco LTHR.\n\n"
            "Si las trazas salen fragmentadas:\n"
            "Sube ligeramente DTHR."
        ),
        "confidence": "Confianza de Recomendación",
        "about": "Acerca de",
        "license": "Licencia MIT",
        "profile_loaded": "Perfil {profile} cargado.",
        "mode_selected": "Modo {mode} seleccionado.",
        "input_selected": "Ráster de entrada seleccionado.",
        "output_selected": "Carpeta de salida seleccionada.",
        "need_input_first": "Primero selecciona un GeoTIFF de entrada.",
        "need_input": "Selecciona un GeoTIFF de entrada.",
        "need_output": "Selecciona una carpeta de salida.",
        "need_rgb": "MIRAGE acepta GeoTIFF monobanda, RGB (3 bandas), o RGBA con alfa en la banda 4.",
        "scores": "Puntajes",
        "metrics": "Métricas",
        "high": "Confianza alta",
        "moderate": "Confianza moderada",
        "low": "Confianza baja",
        "best": "{confidence}. Mejor ajuste: {top} (margen {margin} sobre {second}).",
        "analyzed": "Ráster analizado y recomendaciones aplicadas.",
        "rec_title": "Recomendación de ráster",
        "rec_msg": (
            "Perfil recomendado: {profile}\n"
            "Modo recomendado: {mode}\n"
            "Tipo de ráster: {family}\n\n"
            "Confianza: {confidence}\n"
            "Margen primero-vs-segundo: {margin}\n\n"
            "Razón: {reason}\n\n"
            "Se aplicaron los parámetros sugeridos, y aún puedes editarlos manualmente."
        ),
        "auto_fail": "Falló la estimación automática de parámetros.",
        "auto_error": "Error de auto-parámetros",
        "running": "Ejecutando extracción...",
        "ok": "Extracción completada correctamente.",
        "done_title": "Terminado",
        "done_msg": (
            "La extracción de lineamientos se completó correctamente.\n\n"
            "Los archivos se escribieron en la carpeta de salida seleccionada.\n\n"
            "Reporte:\n{report}"
        ),
        "preview_title": "Vista previa",
        "preview_ready": "Vista previa generada y abierta.",
        "preview_missing": "Primero ejecuta la extracción para previsualizar lineamientos.",
        "preview_fail": "No se pudo generar la vista previa.",
        "fail": "La extracción falló.",
        "error": "Error",
        "no_raster": "Aún no se analizó ningún ráster.",
        "analyze_prompt": "Analiza un ráster para ver puntajes y confianza.",
        "metric_contrast": "Contraste",
        "metric_edge_density": "Densidad de bordes",
        "metric_local_variance": "Varianza local",
        "metric_circle": "Evidencia circular",
        "metric_road": "Evidencia lineal antropogénica",
        "metric_lineation": "Direccionalidad de lineamientos",
        "metric_anomaly": "Saliencia de anomalía",
        "geophys_filters_label": "Filtros Geofísicos (TDR, AS, VDR1, VDR2, THDR)",
        "geophys_type_label": "Tipo de Estructura (trough / ridge)",
        "geophys_stride_label": "Paso de Curvatura (1=3x3, 2=5x5, 3=7x7)",
    },
}

PROFILE_SUMMARIES = {
    "en": {name: cfg["summary"] for name, cfg in PRESETS.items()},
    "es": {
        "Structural continuity": "Ideal cuando buscas firmas naturales más limpias y evitar delinear cada borde posible.",
        "Geo-arch balance": "Buen punto de partida cuando importa la expresión geométrica y aún quieres un resultado controlado.",
        "Anthropogenic detail": "Conserva más respuestas débiles, cortas e irregulares cuando la evidencia sutil es importante.",
        "Magnetometry": "Optimizado para magnetometría de alta resolución para delinear diques y límites estructurales.",
        "Gravimetry": "Optimizado para mapas de anomalías de gravedad regional para definir basamentos y dominios estructurales profundos.",
    },
}

MODE_LABELS = {
    "en": {
        "Geological signature": "Geological signature",
        "Archaeological signature": "Archaeological signature",
        "Geophysics Potential Fields": "Geophysics Potential Fields",
    },
    "es": {
        "Geological signature": "Firma geológica",
        "Archaeological signature": "Firma arqueológica",
        "Geophysics Potential Fields": "Campos potenciales geofísicos",
    },
}

MODE_SUMMARIES = {
    "en": {name: cfg["summary"] for name, cfg in FEATURE_MODES.items()},
    "es": {
        "Geological signature": (
            "Orientaciones preferenciales asociadas a esfuerzos tectónicos, comportamiento "
            "fractal/auto-similar y resiliencia ante ruido natural alto (topografía y vegetación)."
        ),
        "Archaeological signature": (
            "Patrones antropogénicos/localizados con menor dependencia de orientación regional, "
            "preservando círculos, trazas rectilíneas y geometrías tipo pipe bajo micro-relieve perturbado."
        ),
        "Geophysics Potential Fields": (
            "Estructuras geológicas (fallas, zonas de cizalla, diques, contactos) extraídas de datos de "
            "gravedad y magnéticos usando curvatura cuadrática local y fusión multifiltro."
        ),
    },
}

RASTER_FAMILY_LABELS = {
    "en": {
        "geological structural raster": "geological structural raster",
        "archaeological geometry raster": "archaeological geometry raster",
        "satellite optical raster": "satellite optical raster",
        "morphometric enhancement raster": "morphometric enhancement raster",
        "geological magnetic raster": "geological magnetic raster",
        "archaeological magnetic raster": "archaeological magnetic raster",
    },
    "es": {
        "geological structural raster": "ráster geológico estructural",
        "archaeological geometry raster": "ráster arqueológico geométrico",
        "satellite optical raster": "ráster satelital óptico",
        "morphometric enhancement raster": "ráster de realce morfométrico",
        "geological magnetic raster": "ráster magnético geológico",
        "archaeological magnetic raster": "ráster magnético arqueológico",
    },
}


class LineamentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MIRAGE")
        self.root.geometry("980x760")
        self.root.minsize(900, 700)
        self.language = "en"
        self.logo_image_full = None
        self.logo_header_image = None

        self.status_var = tk.StringVar(value=UI_TEXT[self.language]["ready"])
        self.profile_var = tk.StringVar(value="Structural continuity")
        self.summary_var = tk.StringVar(value=PROFILE_SUMMARIES[self.language]["Structural continuity"])
        self.feature_mode_var = tk.StringVar(value="Geological signature")
        self.feature_mode_summary_var = tk.StringVar(value=MODE_SUMMARIES[self.language]["Geological signature"])
        self.recommendation_confidence_var = tk.StringVar(value=UI_TEXT[self.language]["no_raster"])
        self.recommendation_metrics_var = tk.StringVar(value=UI_TEXT[self.language]["analyze_prompt"])
        self.last_lineaments_path = None
        self.params = {}

        self._load_branding_assets()
        self._configure_style()
        self._setup_scroll_container()
        self._build_layout()
        self._apply_preset("Structural continuity")
        self._load_previous_session()

    def _t(self, key):
        return UI_TEXT[self.language][key]

    def _bind_auto_wrap(self, label, parent, padding=30):
        def _on_configure(event):
            if event.widget == parent:
                avail_width = event.width - padding
                if avail_width > 50:
                    label.configure(wraplength=avail_width)
        parent.bind("<Configure>", _on_configure, add="+")

    def _family_label(self, family_key):
        return RASTER_FAMILY_LABELS[self.language].get(family_key, family_key)

    def _configure_style(self):
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        self.root.configure(bg=THEME["bg"])
        style.configure("App.TFrame", background=THEME["bg"])
        style.configure("Card.TFrame", background=THEME["card"], relief="flat")
        style.configure("Header.TLabel", background=THEME["bg"], foreground=THEME["header_fg"], font=("Segoe UI Semibold", 22))
        style.configure("Sub.TLabel", background=THEME["bg"], foreground=THEME["sub_fg"], font=("Segoe UI", 10))
        style.configure("Section.TLabelframe", background=THEME["card"], foreground=THEME["section_fg"])
        style.configure(
            "Section.TLabelframe.Label",
            background=THEME["card"],
            foreground=THEME["section_fg"],
            font=("Segoe UI Semibold", 11),
        )
        style.configure("Body.TLabel", background=THEME["card"], foreground=THEME["body_fg"], font=("Segoe UI", 10))
        style.configure("Hint.TLabel", background=THEME["card"], foreground=THEME["hint_fg"], font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=THEME["status_bg"], foreground=THEME["status_fg"], font=("Segoe UI", 10))
        style.configure(
            "TButton",
            background="#24364e",
            foreground=THEME["status_fg"],
            bordercolor="#2f4868",
        )
        style.map(
            "TButton",
            background=[("active", "#2d4667")],
            foreground=[("active", THEME["status_fg"])],
        )
        style.configure(
            "Run.TButton",
            font=("Segoe UI Semibold", 11),
            background=THEME["accent"],
            foreground=THEME["status_fg"],
            bordercolor=THEME["accent"],
            focusthickness=1,
        )
        style.map(
            "Run.TButton",
            background=[("active", THEME["accent_hover"])],
            foreground=[("active", THEME["status_fg"])],
        )

    def _setup_scroll_container(self):
        self.main_canvas = tk.Canvas(
            self.root,
            bg=THEME["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.main_canvas.pack(side="left", fill="both", expand=True)

        self.v_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.v_scrollbar.pack(side="right", fill="y")
        self.main_canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.scroll_root = ttk.Frame(self.main_canvas, style="App.TFrame")
        self.canvas_window_id = self.main_canvas.create_window((0, 0), window=self.scroll_root, anchor="nw")

        self.scroll_root.bind("<Configure>", self._on_scroll_root_configure)
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.main_canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.main_canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _on_scroll_root_configure(self, _event=None):
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.main_canvas.itemconfigure(self.canvas_window_id, width=event.width)

    def _on_mousewheel(self, event):
        # Windows / macOS
        delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            self.main_canvas.yview_scroll(delta, "units")

    def _on_mousewheel_linux(self, event):
        # Linux
        if event.num == 4:
            self.main_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.main_canvas.yview_scroll(1, "units")

    def _load_branding_assets(self):
        try:
            from PIL import Image, ImageTk
            logo_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "assets", "branding", "logo.png")
            )
            if not os.path.exists(logo_path):
                return

            pil_img = Image.open(logo_path)
            # Resize image to a crisp 128x128 for icon and 50x50 for header
            icon_img = pil_img.resize((128, 128), Image.Resampling.LANCZOS)
            self.logo_image_full = ImageTk.PhotoImage(icon_img)

            header_img = pil_img.resize((50, 50), Image.Resampling.LANCZOS)
            self.logo_header_image = ImageTk.PhotoImage(header_img)

            self.root.iconphoto(True, self.logo_image_full)
        except Exception as e:
            print("Error loading branding assets:", e)
            self.logo_image_full = None
            self.logo_header_image = None

    def _load_previous_session(self):
        try:
            import json
            session_path = os.path.join(os.path.expanduser("~"), ".mirage_session.json")
            if os.path.exists(session_path):
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "input" in data and os.path.exists(data["input"]):
                        self.input_entry.delete(0, tk.END)
                        self.input_entry.insert(0, data["input"])
                    if "output" in data and os.path.exists(data["output"]):
                        self.output_entry.delete(0, tk.END)
                        self.output_entry.insert(0, data["output"])
        except Exception as e:
            print("Error loading session:", e)

    def _save_current_session(self):
        try:
            import json
            session_path = os.path.join(os.path.expanduser("~"), ".mirage_session.json")
            data = {
                "input": self.input_entry.get().strip(),
                "output": self.output_entry.get().strip()
            }
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error saving session:", e)

    def _capture_form_state(self):
        state = {
            "input": "",
            "output": "",
            "params": {},
            "profile": self.profile_var.get(),
            "mode": self.feature_mode_var.get(),
        }
        if hasattr(self, "input_entry"):
            state["input"] = self.input_entry.get()
        if hasattr(self, "output_entry"):
            state["output"] = self.output_entry.get()
        for key, entry in self.params.items():
            state["params"][key] = entry.get()
            
        if self.feature_mode_var.get() == "Geophysics Potential Fields":
            state["geophys_filters"] = self.geophys_filters_entry.get()
            state["geophys_type"] = self.geophys_type_box.get()
            state["geophys_stride"] = self.geophys_stride_box.get()
            
        return state

    def _restore_form_state(self, state):
        self.profile_var.set(state["profile"])
        self.feature_mode_var.set(state["mode"])

        if state["input"]:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, state["input"])
        if state["output"]:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, state["output"])

        if state["params"]:
            for key, value in state["params"].items():
                if key in self.params:
                    self.params[key].delete(0, tk.END)
                    self.params[key].insert(0, value)

        if "geophys_filters" in state:
            self.geophys_filters_entry.delete(0, tk.END)
            self.geophys_filters_entry.insert(0, state["geophys_filters"])
            self.geophys_type_box.set(state["geophys_type"])
            self.geophys_stride_box.set(state["geophys_stride"])
            self.geophys_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        else:
            self.geophys_frame.grid_forget()

        self.summary_var.set(PROFILE_SUMMARIES[self.language][self.profile_var.get()])
        self.feature_mode_summary_var.set(MODE_SUMMARIES[self.language][self.feature_mode_var.get()])

    def toggle_language(self):
        state = self._capture_form_state()
        self.language = "es" if self.language == "en" else "en"
        self._build_layout()
        self._restore_form_state(state)
        self.status_var.set(self._t("ready"))

    def _build_layout(self):
        if hasattr(self, "outer") and self.outer is not None:
            self.outer.destroy()

        self.outer = ttk.Frame(self.scroll_root, style="App.TFrame", padding=18)
        self.outer.pack(fill="both", expand=True)
        self.outer.columnconfigure(0, weight=3)
        self.outer.columnconfigure(1, weight=2)
        self.outer.rowconfigure(1, weight=1)

        header = ttk.Frame(self.outer, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        header.columnconfigure(1, weight=1)

        if self.logo_header_image is not None:
            logo_label = tk.Label(header, image=self.logo_header_image, bg=THEME["bg"], bd=0, highlightthickness=0)
            logo_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))

        ttk.Label(header, text=self._t("header"), style="Header.TLabel").grid(row=0, column=1, sticky="w")
        lbl_subtitle = ttk.Label(
            header,
            text=self._t("subtitle"),
            style="Sub.TLabel",
            justify="left",
        )
        lbl_subtitle.grid(row=1, column=1, sticky="ew", pady=(4, 0))
        self._bind_auto_wrap(lbl_subtitle, header, padding=120)
        ttk.Button(header, text=self._t("lang_button"), command=self.toggle_language).grid(row=0, column=2, rowspan=2, sticky="e")

        left = ttk.Frame(self.outer, style="Card.TFrame", padding=16)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(self.outer, style="Card.TFrame", padding=16)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        self._build_data_section(left)
        self._build_profile_section(left)
        self._build_feature_mode_section(left)
        self._build_parameters_section(left)
        self._build_actions_section(left)
        self._build_side_panel(right)

        status_bar = ttk.Label(
            self.outer,
            textvariable=self.status_var,
            style="Status.TLabel",
            anchor="w",
            padding=(12, 10),
        )
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_data_section(self, parent):
        section = ttk.LabelFrame(parent, text=self._t("data"), style="Section.TLabelframe", padding=14)
        section.grid(row=0, column=0, sticky="ew")
        section.columnconfigure(1, weight=1)

        ttk.Label(section, text=self._t("input"), style="Body.TLabel").grid(row=0, column=0, sticky="w")
        self.input_entry = ttk.Entry(section)
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(section, text=self._t("browse"), command=self.browse_input).grid(row=0, column=2)

        ttk.Label(section, text=self._t("output"), style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.output_entry = ttk.Entry(section)
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(section, text=self._t("browse"), command=self.browse_output_folder).grid(row=1, column=2, pady=(10, 0))

    def _build_profile_section(self, parent):
        section = ttk.LabelFrame(parent, text=self._t("profile_section"), style="Section.TLabelframe", padding=14)
        section.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        section.columnconfigure(1, weight=1)

        ttk.Label(section, text=self._t("profile"), style="Body.TLabel").grid(row=0, column=0, sticky="w")
        profile_box = ttk.Combobox(
            section,
            textvariable=self.profile_var,
            values=list(PRESETS.keys()),
            state="readonly",
        )
        profile_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        profile_box.bind("<<ComboboxSelected>>", self.on_profile_change)

        lbl_profile_summary = ttk.Label(section, textvariable=self.summary_var, style="Hint.TLabel", justify="left")
        lbl_profile_summary.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self._bind_auto_wrap(lbl_profile_summary, section, padding=36)

        btn_row = ttk.Frame(section, style="Card.TFrame")
        btn_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(btn_row, text=self._t("apply"), command=lambda: self._apply_preset(self.profile_var.get())).pack(side="left")
        ttk.Button(btn_row, text=self._t("analyze"), command=self.auto_calculate_parameters).pack(side="left", padx=(8, 0))

    def _build_feature_mode_section(self, parent):
        section = ttk.LabelFrame(parent, text=self._t("mode_section"), style="Section.TLabelframe", padding=14)
        section.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        section.columnconfigure(1, weight=1)

        ttk.Label(section, text=self._t("mode"), style="Body.TLabel").grid(row=0, column=0, sticky="w")
        mode_box = ttk.Combobox(
            section,
            textvariable=self.feature_mode_var,
            values=list(FEATURE_MODES.keys()),
            state="readonly",
        )
        mode_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        mode_box.bind("<<ComboboxSelected>>", self.on_feature_mode_change)

        lbl_mode_summary = ttk.Label(
            section,
            textvariable=self.feature_mode_summary_var,
            style="Hint.TLabel",
            justify="left",
        )
        lbl_mode_summary.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self._bind_auto_wrap(lbl_mode_summary, section, padding=36)

        # Geophysics dynamic panel
        self.geophys_frame = ttk.Frame(section, style="Card.TFrame")
        self.geophys_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.geophys_frame, text=self._t("geophys_filters_label"), style="Body.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.geophys_filters_entry = ttk.Entry(self.geophys_frame)
        self.geophys_filters_entry.insert(0, "TDR,AS")
        self.geophys_filters_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        
        ttk.Label(self.geophys_frame, text=self._t("geophys_type_label"), style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.geophys_type_box = ttk.Combobox(self.geophys_frame, values=["trough", "ridge"], state="readonly")
        self.geophys_type_box.set("trough")
        self.geophys_type_box.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        
        ttk.Label(self.geophys_frame, text=self._t("geophys_stride_label"), style="Body.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        self.geophys_stride_box = ttk.Spinbox(self.geophys_frame, from_=1, to=5, width=5)
        self.geophys_stride_box.set(1)
        self.geophys_stride_box.grid(row=2, column=1, sticky="w", padx=8, pady=4)

    def _build_parameters_section(self, parent):
        section = ttk.LabelFrame(parent, text=self._t("params"), style="Section.TLabelframe", padding=14)
        section.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        section.columnconfigure(1, weight=1)

        self.params = {}
        for row, name in enumerate(("RADI", "GTHR", "LTHR", "FTHR", "ATHR", "DTHR")):
            ttk.Label(section, text=name, style="Body.TLabel").grid(row=row, column=0, sticky="nw", pady=(0, 10))
            field = ttk.Entry(section, width=10)
            field.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(0, 10))
            ttk.Label(section, text=PARAM_INFO[name], style="Hint.TLabel", wraplength=360, justify="left").grid(
                row=row, column=2, sticky="w", padx=(12, 0), pady=(0, 10)
            )
            self.params[name] = field

    def _build_actions_section(self, parent):
        section = ttk.Frame(parent, style="Card.TFrame", padding=(0, 14, 0, 0))
        section.grid(row=4, column=0, sticky="ew")
        section.columnconfigure(0, weight=1)
        section.columnconfigure(1, weight=1)

        self.run_button = ttk.Button(section, text=self._t("run"), command=self.run_extraction, style="Run.TButton")
        self.run_button.grid(row=0, column=0, sticky="ew")
        ttk.Button(section, text=self._t("preview"), command=self.preview_lineaments).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )
        lbl_hint = ttk.Label(
            section,
            text=self._t("hint"),
            style="Hint.TLabel",
            justify="left",
        )
        lbl_hint.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self._bind_auto_wrap(lbl_hint, section, padding=20)

    def _build_side_panel(self, parent):
        purpose = ttk.LabelFrame(parent, text=self._t("priorities"), style="Section.TLabelframe", padding=14)
        purpose.grid(row=0, column=0, sticky="ew")
        purpose.columnconfigure(0, weight=1)
        lbl_purpose = ttk.Label(
            purpose,
            text=self._t("priorities_body"),
            style="Body.TLabel",
            justify="left",
        )
        lbl_purpose.grid(row=0, column=0, sticky="ew")
        self._bind_auto_wrap(lbl_purpose, purpose, padding=36)

        tips = ttk.LabelFrame(parent, text=self._t("tuning"), style="Section.TLabelframe", padding=14)
        tips.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        tips.columnconfigure(0, weight=1)
        lbl_tips = ttk.Label(
            tips,
            text=self._t("tuning_body"),
            style="Body.TLabel",
            justify="left",
        )
        lbl_tips.grid(row=0, column=0, sticky="ew")
        self._bind_auto_wrap(lbl_tips, tips, padding=36)

        confidence = ttk.LabelFrame(parent, text=self._t("confidence"), style="Section.TLabelframe", padding=14)
        confidence.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        confidence.columnconfigure(0, weight=1)
        lbl_conf = ttk.Label(
            confidence,
            textvariable=self.recommendation_confidence_var,
            style="Body.TLabel",
            justify="left",
        )
        lbl_conf.grid(row=0, column=0, sticky="ew")
        self._bind_auto_wrap(lbl_conf, confidence, padding=36)

        lbl_metrics = ttk.Label(
            confidence,
            textvariable=self.recommendation_metrics_var,
            style="Hint.TLabel",
            justify="left",
        )
        lbl_metrics.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self._bind_auto_wrap(lbl_metrics, confidence, padding=36)

        about = ttk.LabelFrame(parent, text=self._t("about"), style="Section.TLabelframe", padding=14)
        about.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        author = tk.Label(
            about,
            text="Zavaleta, J.",
            fg=THEME["link_fg"],
            bg=THEME["card"],
            cursor="hand2",
            font=("Segoe UI", 10, "underline"),
        )
        author.grid(row=0, column=0, sticky="w")
        author.bind("<Button-1>", lambda e: webbrowser.open("https://linkedin.com/in/jordan-zav"))
        ttk.Label(
            about,
            text=self._t("license"),
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _apply_preset(self, preset_name):
        preset = PRESETS[preset_name]
        for key, entry in self.params.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(preset[key]))
        self.profile_var.set(preset_name)
        self.summary_var.set(PROFILE_SUMMARIES[self.language][preset_name])
        self.status_var.set(self._t("profile_loaded").format(profile=preset_name))

    def on_profile_change(self, _event=None):
        self._apply_preset(self.profile_var.get())

    def on_feature_mode_change(self, _event=None):
        mode_key = self.feature_mode_var.get()
        self.feature_mode_summary_var.set(MODE_SUMMARIES[self.language][mode_key])
        self.status_var.set(self._t("mode_selected").format(mode=MODE_LABELS[self.language][mode_key]))
        
        if mode_key == "Campos potenciales geofísicos" or mode_key == "Geophysics Potential Fields":
            self.geophys_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        else:
            self.geophys_frame.grid_forget()

    def browse_input(self):
        paths = filedialog.askopenfilenames(filetypes=[("GeoTIFF files", "*.tif *.tiff")])
        if paths:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, "; ".join(paths))
            self.status_var.set(self._t("input_selected"))
            self._save_current_session()

    def browse_output_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)
            self.status_var.set(self._t("output_selected"))
            self._save_current_session()

    def auto_calculate_parameters(self):
        try:
            infile_str = self.input_entry.get()
            if not infile_str:
                raise ValueError(self._t("need_input_first"))
            infiles = [f.strip() for f in infile_str.split(";") if f.strip()]
            if not infiles:
                raise ValueError(self._t("need_input_first"))
            infile = infiles[0]
            validate_rgb_geotiff(infile)

            with rasterio.open(infile) as src:
                h, w = src.height, src.width
                scale = min(1.0, AUTO_READ_MAX_DIM / float(max(h, w)))
                out_h = max(64, int(round(h * scale)))
                out_w = max(64, int(round(w * scale)))
                interps = tuple(src.colorinterp or ())
                source_hint = {
                    "is_true_color_rgb": (
                        len(interps) >= 3
                        and interps[0] == ColorInterp.red
                        and interps[1] == ColorInterp.green
                        and interps[2] == ColorInterp.blue
                    )
                }
                if src.count == 1:
                    data = src.read(
                        1,
                        out_shape=(out_h, out_w),
                        resampling=Resampling.bilinear,
                    ).astype(np.float32)
                else:
                    data = src.read(
                        indexes=[1, 2, 3],
                        out_shape=(3, out_h, out_w),
                        resampling=Resampling.bilinear,
                    ).astype(np.float32)
                pixel_size = abs(src.transform.a) * (h / float(out_h))

            recommendation = recommend_settings(data, pixel_size, source_hint=source_hint)
            suggested = recommendation["params"]

            self._apply_preset(recommendation["profile"])
            self.feature_mode_var.set(recommendation["feature_mode"])
            self.feature_mode_summary_var.set(MODE_SUMMARIES[self.language][recommendation["feature_mode"]])

            for key, entry in self.params.items():
                if key in suggested:
                    entry.delete(0, tk.END)
                    entry.insert(0, str(suggested[key]))

            first_name = Path(infile).name
            if len(infiles) > 1:
                self.summary_var.set(
                    f"Recommended {recommendation['profile']} profile for a {self._family_label(recommendation['raster_family'])} (Analyzed: {first_name})."
                    if self.language == "en"
                    else f"Perfil {recommendation['profile']} recomendado para {self._family_label(recommendation['raster_family'])} (Analizado: {first_name})."
                )
            else:
                self.summary_var.set(
                    f"Recommended {recommendation['profile']} profile for a {self._family_label(recommendation['raster_family'])}."
                    if self.language == "en"
                    else f"Perfil {recommendation['profile']} recomendado para {self._family_label(recommendation['raster_family'])}."
                )

            sorted_scores = sorted(recommendation["mode_scores"].items(), key=lambda item: item[1], reverse=True)
            top_name, top_score = sorted_scores[0]
            second_name, second_score = sorted_scores[1]
            margin = round(top_score - second_score, 3)
            if margin >= 1.5:
                confidence = self._t("high")
            elif margin >= 0.6:
                confidence = self._t("moderate")
            else:
                confidence = self._t("low")

            self.recommendation_confidence_var.set(
                self._t("best").format(
                    confidence=confidence,
                    top=MODE_LABELS[self.language][top_name],
                    margin=margin,
                    second=MODE_LABELS[self.language][second_name],
                )
            )
            self.recommendation_metrics_var.set(
                f"{self._t('scores')}\n"
                f"{MODE_LABELS[self.language]['Geological signature']}: {recommendation['mode_scores']['Geological signature']}\n"
                f"{MODE_LABELS[self.language]['Archaeological signature']}: {recommendation['mode_scores']['Archaeological signature']}\n\n"
                f"{self._t('metrics')}\n"
                f"{self._t('metric_contrast')}: {recommendation['metrics']['contrast']}\n"
                f"{self._t('metric_edge_density')}: {recommendation['metrics']['edge_density']}\n"
                f"{self._t('metric_local_variance')}: {recommendation['metrics']['local_variance']}\n"
                f"{self._t('metric_circle')}: {recommendation['metrics'].get('circle_evidence', 0.0)}\n"
                f"{self._t('metric_road')}: {recommendation['metrics'].get('road_evidence', 0.0)}\n"
                f"{self._t('metric_lineation')}: {recommendation['metrics'].get('lineation_directionality', 0.0)}\n"
                f"{self._t('metric_anomaly')}: {recommendation['metrics'].get('anomaly_salience', 0.0)}"
            )
            self.status_var.set(self._t("analyzed"))
            messagebox.showinfo(
                self._t("rec_title"),
                self._t("rec_msg").format(
                    profile=recommendation["profile"],
                    mode=MODE_LABELS[self.language][recommendation["feature_mode"]],
                    family=self._family_label(recommendation["raster_family"]),
                    confidence=confidence,
                    margin=margin,
                    reason=(recommendation.get("reason_es") if self.language == "es" else recommendation["reason"]),
                ),
            )
        except Exception as exc:
            self.status_var.set(self._t("auto_fail"))
            messagebox.showerror(self._t("auto_error"), str(exc))

    def run_extraction(self):
        import threading

        infile_str = self.input_entry.get().strip()
        out_dir = self.output_entry.get().strip()
        if not infile_str:
            messagebox.showerror(self._t("error"), self._t("need_input"))
            return
        if not out_dir:
            messagebox.showerror(self._t("error"), self._t("need_output"))
            return

        self._save_current_session()

        infiles = [f.strip() for f in infile_str.split(";") if f.strip()]
        if not infiles:
            messagebox.showerror(self._t("error"), self._t("need_input"))
            return

        try:
            for f in infiles:
                validate_rgb_geotiff(f)
        except Exception as exc:
            messagebox.showerror(self._t("error"), str(exc))
            return

        self.status_var.set(self._t("running"))
        self.run_button.configure(state="disabled")

        def target():
            try:
                mode_key = self.feature_mode_var.get()
                is_geophys = (mode_key == "Campos potenciales geofísicos" or mode_key == "Geophysics Potential Fields")
                geophys_filters = self.geophys_filters_entry.get().strip() if is_geophys else None
                geophys_extract_type = self.geophys_type_box.get() if is_geophys else "trough"
                try:
                    geophys_stride = int(self.geophys_stride_box.get()) if is_geophys else 1
                except ValueError:
                    geophys_stride = 1

                use_subdirs = len(infiles) > 1
                last_summary = None

                for idx, f in enumerate(infiles):
                    if use_subdirs:
                        current_out_dir = str(Path(out_dir) / Path(f).stem)
                        self.root.after(0, lambda f=f, idx=idx: self.status_var.set(
                            f"{self._t('running')} ({idx+1}/{len(infiles)}): {Path(f).name}"
                        ))
                    else:
                        current_out_dir = out_dir

                    summary = run_extraction_job(
                        geotiff=f,
                        out_dir=current_out_dir,
                        radi=int(self.params["RADI"].get()),
                        gthr=int(self.params["GTHR"].get()),
                        lthr=int(self.params["LTHR"].get()),
                        fthr=float(self.params["FTHR"].get()),
                        athr=float(self.params["ATHR"].get()),
                        dthr=float(self.params["DTHR"].get()),
                        extraction_mode=FEATURE_MODES[mode_key]["value"],
                        geophys_filters=geophys_filters,
                        geophys_extract_type=geophys_extract_type,
                        geophys_stride=geophys_stride,
                    )
                    last_summary = summary

                self.last_lineaments_path = last_summary["outputs"]["lineaments"]
                self.root.after(0, lambda: self._on_extraction_success(out_dir, use_subdirs, infiles))
            except Exception as exc:
                self.root.after(0, lambda: self._on_extraction_failure(exc))

        threading.Thread(target=target, daemon=True).start()

    def _on_extraction_success(self, out_dir, use_subdirs=False, infiles=None):
        self.status_var.set(self._t("ok"))
        self.run_button.configure(state="normal")
        if use_subdirs and infiles:
            msg = (
                f"Lineament extraction completed successfully.\n\n"
                f"A subfolder was created for each of the {len(infiles)} inputs in:\n{out_dir}"
            )
            if self.language == "es":
                msg = (
                    f"La extracción de lineamientos se completó correctamente.\n\n"
                    f"Se creó una carpeta para cada uno de los {len(infiles)} archivos de entrada en:\n{out_dir}"
                )
            messagebox.showinfo(self._t("done_title"), msg)
        else:
            messagebox.showinfo(
                self._t("done_title"),
                self._t("done_msg").format(report=os.path.join(out_dir, "mirage_report.json")),
            )

    def _on_extraction_failure(self, exc):
        self.status_var.set(self._t("fail"))
        self.run_button.configure(state="normal")
        messagebox.showerror(self._t("error"), str(exc))

    def _draw_polyline(self, canvas, rows, cols, color):
        if len(rows) < 2:
            return
        for i in range(len(rows) - 1):
            rr, cc = sk_line(int(rows[i]), int(cols[i]), int(rows[i + 1]), int(cols[i + 1]))
            valid = (rr >= 0) & (rr < canvas.shape[0]) & (cc >= 0) & (cc < canvas.shape[1])
            rr = rr[valid]
            cc = cc[valid]
            canvas[rr, cc] = color
            rr2 = np.clip(rr + 1, 0, canvas.shape[0] - 1)
            cc2 = np.clip(cc + 1, 0, canvas.shape[1] - 1)
            canvas[rr2, cc] = color
            canvas[rr, cc2] = color

    def preview_lineaments(self):
        try:
            infile_str = self.input_entry.get().strip()
            out_dir = self.output_entry.get().strip()
            infiles = [f.strip() for f in infile_str.split(";") if f.strip()]
            if not infiles:
                raise ValueError(self._t("preview_missing"))

            if self.last_lineaments_path and os.path.exists(self.last_lineaments_path):
                shp = self.last_lineaments_path
                infile = infiles[-1]
            else:
                infile = infiles[-1]
                if len(infiles) > 1:
                    shp = os.path.join(out_dir, Path(infile).stem, "lineaments.shp")
                else:
                    shp = os.path.join(out_dir, "lineaments.shp")

            if not os.path.exists(infile) or not os.path.exists(shp):
                raise ValueError(self._t("preview_missing"))
            validate_rgb_geotiff(infile)

            with rasterio.open(infile) as src:
                h, w = src.height, src.width
                max_dim = 1400
                scale = min(1.0, max_dim / float(max(h, w)))
                out_h = max(64, int(round(h * scale)))
                out_w = max(64, int(round(w * scale)))
                if src.count == 1:
                    gray = src.read(
                        1,
                        out_shape=(out_h, out_w),
                        resampling=Resampling.bilinear,
                    ).astype(np.float32)
                    rgb = np.stack([gray, gray, gray], axis=0)
                else:
                    rgb = src.read(
                        indexes=[1, 2, 3],
                        out_shape=(3, out_h, out_w),
                        resampling=Resampling.bilinear,
                    ).astype(np.float32)
                preview_transform = src.transform * src.transform.scale(w / float(out_w), h / float(out_h))
                crs = src.crs

            for b in range(3):
                p2, p98 = np.percentile(rgb[b], [2, 98])
                rgb[b] = np.clip((rgb[b] - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)
            canvas = (np.transpose(rgb, (1, 2, 0)) * 255.0).astype(np.uint8)

            gdf = gpd.read_file(shp)
            if crs and gdf.crs and str(gdf.crs) != str(crs):
                gdf = gdf.to_crs(crs)

            inv = ~preview_transform
            color = np.array([255, 40, 40], dtype=np.uint8)
            for geom in gdf.geometry:
                if geom is None or geom.is_empty:
                    continue
                geoms = [geom] if geom.geom_type == "LineString" else list(getattr(geom, "geoms", []))
                for ln in geoms:
                    coords = np.asarray(ln.coords)
                    if len(coords) < 2:
                        continue
                    cols = []
                    rows = []
                    for x, y in coords:
                        c, r = inv * (float(x), float(y))
                        cols.append(int(round(c)))
                        rows.append(int(round(r)))
                    self._draw_polyline(canvas, rows, cols, color)

            preview_path = os.path.join(out_dir or os.path.dirname(infile), "lineaments_preview.tif")
            with rasterio.open(
                preview_path,
                "w",
                driver="GTiff",
                height=canvas.shape[0],
                width=canvas.shape[1],
                count=3,
                dtype=canvas.dtype,
                crs=crs,
                transform=preview_transform,
            ) as dst:
                dst.write(np.transpose(canvas, (2, 0, 1)))

            os.startfile(preview_path)
            self.status_var.set(self._t("preview_ready"))
        except Exception as exc:
            self.status_var.set(self._t("preview_fail"))
            messagebox.showerror(self._t("preview_title"), str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    app = LineamentGUI(root)
    root.mainloop()
