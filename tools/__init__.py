"""Hailey tools package."""

def closeEvent(self, event):

    if self.worker is not None and self.worker.isRunning():

        print("[Hailey] Wachten op actieve worker...")

        self.worker.wait()

    event.accept()