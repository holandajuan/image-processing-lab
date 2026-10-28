"""Interface simples para a atividade de Processamento Digital de Imagens."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk

from processing import OPERATIONS, image_histograms, load_image, process_image


class ImageProcessingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.original: Image.Image | None = None
        self.result: Image.Image | None = None
        self.preview_images: list[ImageTk.PhotoImage] = []
        self.resize_job: str | None = None

        root.title("Processamento Digital de Imagens")
        root.geometry("1100x800")
        root.minsize(880, 680)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        main = ttk.Frame(root, padding=16)
        main.grid(sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=3)
        main.rowconfigure(4, weight=2)

        ttk.Label(main, text="Processamento Digital de Imagens", font=("Segoe UI", 18, "bold")).grid(
            row=0, sticky="w", pady=(0, 12)
        )

        toolbar = ttk.Frame(main)
        toolbar.grid(row=1, sticky="ew", pady=(0, 12))
        ttk.Button(toolbar, text="Abrir imagem…", command=self.open_image).pack(side="left")
        self.save_button = ttk.Button(toolbar, text="Salvar resultado…", command=self.save_image, state="disabled")
        self.save_button.pack(side="left", padx=8)
        self.reset_button = ttk.Button(toolbar, text="Restaurar original", command=self.reset, state="disabled")
        self.reset_button.pack(side="left")
        self.histogram_log_scale = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            toolbar,
            text="Histogramas em escala logarítmica",
            variable=self.histogram_log_scale,
            command=self.draw_histograms,
        ).pack(side="right")

        controls = ttk.LabelFrame(main, text="Processamento", padding=10)
        controls.grid(row=2, sticky="ew", pady=(0, 12))
        controls.columnconfigure(1, weight=1)
        self.operation = tk.StringVar(value="Contraste")
        self.operation_picker = ttk.Combobox(
            controls, textvariable=self.operation, values=list(OPERATIONS), state="readonly", width=29
        )
        self.operation_picker.grid(row=0, column=0, sticky="w", padx=(0, 16))
        self.operation_picker.bind("<<ComboboxSelected>>", self.update_adjustment)

        self.factor = tk.DoubleVar(value=1.5)
        self.adjustment_label = ttk.Label(controls)
        self.adjustment_label.grid(row=0, column=1, sticky="w")
        self.factor_label = ttk.Label(controls, width=5, anchor="e")
        self.factor_label.grid(row=0, column=2, padx=(8, 12))
        self.scale = ttk.Scale(controls, variable=self.factor, command=self.show_factor)
        self.scale.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=(6, 0))
        self.apply_button = ttk.Button(controls, text="Aplicar", command=self.apply, state="disabled")
        self.apply_button.grid(row=0, column=3, rowspan=2)
        ttk.Label(controls, text="Cada operação usa a imagem original.").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        previews = ttk.Frame(main)
        previews.grid(row=3, sticky="nsew")
        previews.columnconfigure((0, 1), weight=1, uniform="preview")
        previews.rowconfigure(0, weight=1)
        self.image_labels = []
        for index, title in enumerate(("Imagem original", "Imagem processada")):
            frame = ttk.LabelFrame(previews, text=title, padding=8)
            frame.grid(row=0, column=index, sticky="nsew", padx=(0, 6) if index == 0 else (6, 0))
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            label = ttk.Label(frame, text="Abra uma imagem para começar", anchor="center")
            # place evita que o tamanho da miniatura altere o tamanho da janela.
            label.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.image_labels.append(label)
        previews.bind("<Configure>", self.schedule_previews)

        self.figure = Figure(figsize=(9, 2.6), dpi=100, layout="constrained")
        self.axes = self.figure.subplots(1, 2, sharex=True, sharey=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=main)
        self.canvas.get_tk_widget().grid(row=4, sticky="nsew", pady=(12, 0))

        self.status = tk.StringVar(value="Selecione uma imagem JPG, PNG, BMP, TIFF ou WebP.")
        ttk.Label(main, textvariable=self.status, anchor="w").grid(row=5, sticky="ew", pady=(8, 0))
        self.update_adjustment()
        self.draw_histograms()

    def update_adjustment(self, _event=None) -> None:
        settings = OPERATIONS[self.operation.get()]
        if settings is None:
            self.adjustment_label.configure(text="Esta operação não precisa de ajuste.")
            self.scale.state(["disabled"])
            self.factor_label.configure(text="—")
        else:
            label, minimum, maximum, default = settings
            self.adjustment_label.configure(text=label)
            self.scale.configure(from_=minimum, to=maximum)
            self.scale.state(["!disabled"])
            self.factor.set(default)
            self.show_factor()

    def show_factor(self, _value=None) -> None:
        if OPERATIONS[self.operation.get()] is not None:
            self.factor_label.configure(text=f"{self.factor.get():.2f}")

    def open_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione uma imagem",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"), ("Todos os arquivos", "*.*")],
        )
        if not path:
            return
        try:
            original = load_image(path)
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            messagebox.showerror("Erro ao abrir", f"Não foi possível abrir a imagem.\n\n{error}")
            return

        self.original = original
        self.result = original.copy()
        for button in (self.apply_button, self.save_button, self.reset_button):
            button.state(["!disabled"])
        self.refresh(f"Imagem carregada: {original.width} × {original.height} pixels. Escolha uma operação e clique em Aplicar.")

    def apply(self) -> None:
        if self.original is None:
            return
        try:
            self.result = process_image(self.original, self.operation.get(), self.factor.get())
        except (OSError, ValueError) as error:
            messagebox.showerror("Erro no processamento", str(error))
            return
        detail = f" (ajuste: {self.factor.get():.2f})" if OPERATIONS[self.operation.get()] is not None else ""
        self.refresh(f"Aplicado: {self.operation.get()}{detail}. Resultado em resolução original.")

    def reset(self) -> None:
        if self.original is not None:
            self.result = self.original.copy()
            self.refresh("Resultado restaurado para a imagem original.")

    def save_image(self) -> None:
        if self.result is None:
            return
        path = filedialog.asksaveasfilename(
            title="Salvar imagem processada",
            defaultextension=".png",
            initialfile="imagem_processada.png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp"), ("TIFF", "*.tif")],
        )
        if not path:
            return
        try:
            self.result.save(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Erro ao salvar", f"Não foi possível salvar a imagem.\n\n{error}")
            return
        self.status.set(f"Imagem salva em: {path}")

    def refresh(self, message: str) -> None:
        self.draw_previews()
        self.draw_histograms()
        self.status.set(message)

    def schedule_previews(self, _event=None) -> None:
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(100, self.draw_previews)

    def draw_previews(self) -> None:
        self.resize_job = None
        self.preview_images.clear()
        for label, source in zip(self.image_labels, (self.original, self.result)):
            if source is None:
                continue
            preview = source.copy()
            preview.thumbnail((max(1, label.winfo_width() - 16), max(1, label.winfo_height() - 16)), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(preview)
            self.preview_images.append(photo)
            label.configure(image=photo, text="")

    def draw_histograms(self) -> None:
        log_scale = self.histogram_log_scale.get()
        for ax, source, title in zip(
            self.axes, (self.original, self.result), ("Histograma da original", "Histograma do resultado")
        ):
            ax.clear()
            ax.set_title(title, fontsize=11)
            ax.set_xlabel("Intensidade (0–255)")
            ax.set_ylabel("Quantidade de pixels" + (" (escala logarítmica)" if log_scale else ""))
            ax.set_xlim(0, 255)
            ax.grid(alpha=0.2)
            if source is None:
                ax.set_ylim(0, 1)
            else:
                for name, color, counts in image_histograms(source):
                    ax.plot(range(256), counts, color=color, label=name, linewidth=1, alpha=0.8)
                ax.legend(loc="upper right", fontsize=8)

        # A escala logarítmica destaca frequências menores sem cortar os picos.
        # symlog também representa contagens iguais a zero (trecho linear até 1).
        for ax in self.axes:
            if log_scale:
                ax.set_yscale("symlog", linthresh=1)
            else:
                ax.set_yscale("linear")

        # Os dois gráficos continuam compartilhando a mesma escala vertical.
        if self.original is not None and self.result is not None:
            peak = max(max(counts) for source in (self.original, self.result) for _, _, counts in image_histograms(source))
            self.axes[0].set_ylim(0, max(1, peak * 1.08))
        self.canvas.draw_idle()


if __name__ == "__main__":
    window = tk.Tk()
    ImageProcessingApp(window)
    window.mainloop()
