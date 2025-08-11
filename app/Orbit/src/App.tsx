import Chat from "./components/Chat.tsx";
import "./App.css";
import { useEffect } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";

function App() {
  useEffect(() => {
    // Make sure the window is visible and focused in desktop app mode
    getCurrentWindow().show();
  }, []);

  return (
    <div className="h-screen w-screen bg-app">
      <Chat />
    </div>
  );
}

export default App;
