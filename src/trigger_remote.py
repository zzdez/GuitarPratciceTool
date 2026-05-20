from src.gui import GuitarPracticeApp
app = GuitarPracticeApp()
app.update()
app.open_remote_control()
app.after(1000, app.destroy)
app.mainloop()
