### zara_bridge
Delegate one bounded text turn to an existing Zara daemon.
args: `message`
Use this when Zara's assistant runtime or Zara-owned tools are specifically useful for the task.
Do not use it as a generic retry path or bounce the same request repeatedly between Agent Zero and Zara.
The bridge returns Zara's user-facing response and does not expose the Zara transport protocol to the model.
