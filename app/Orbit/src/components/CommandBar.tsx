import React, { useEffect, useRef, useState } from "react";
import { connectSteps, runCommand, StepEvent } from "../lib/steps";

type CommandBarProps = {
  onStepsOpenChange?: (open: boolean) => void;
};

const CommandBar: React.FC<CommandBarProps> = ({ onStepsOpenChange }) => {
  const [input, setInput] = useState("");
  const [events, setEvents] = useState<StepEvent[]>([]);
  const [isStepsOpen, setIsStepsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const hintTimerRef = useRef<number | null>(null);

  const idleHints = [
    "Open app: Safari",
    "Search files: build.sh",
    "Run tests",
    "Create Jira ticket",
    "Summarize this page",
  ];

  useEffect(() => {
    // Connect to WebSocket for real-time step updates
    wsRef.current = connectSteps((event) => {
      setEvents((prev) => [...prev, event]);
      
      // Auto-open steps panel when a command starts
      if (event.status === "queued" && event.step_id === 1) {
        setIsStepsOpen(true);
      }
    });

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Idle rotating placeholder hints
  useEffect(() => {
    // Rotate only when not typing to avoid distraction
    const shouldRotate = !isFocused && input.trim().length === 0;
    if (shouldRotate) {
      // Change hint every 3 seconds
      hintTimerRef.current = window.setInterval(() => {
        setHintIndex((prev) => (prev + 1) % idleHints.length);
      }, 3000);
    }
    return () => {
      if (hintTimerRef.current) {
        clearInterval(hintTimerRef.current);
        hintTimerRef.current = null;
      }
    };
  }, [isFocused, input, idleHints.length]);

  // Notify parent (for window resize/position) when steps panel visibility changes
  useEffect(() => {
    onStepsOpenChange?.(isStepsOpen);
  }, [isStepsOpen, onStepsOpenChange]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() || isLoading) return;
    
    setIsLoading(true);
    
    try {
      await runCommand(input.trim());
      setInput("");
      setIsStepsOpen(true);
    } catch (error) {
      console.error("Failed to run command:", error);
      // TODO: Show error in UI
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSteps = () => {
    setIsStepsOpen(!isStepsOpen);
  };

  const getStatusColor = (status: StepEvent["status"]) => {
    switch (status) {
      case "ok":
        return "text-green-400";
      case "error":
        return "text-red-400";
      case "running":
        return "text-yellow-400";
      case "queued":
      default:
        return "text-white/70";
    }
  };

  const getStatusIcon = (status: StepEvent["status"]) => {
    switch (status) {
      case "ok":
        return "✓";
      case "error":
        return "✗";
      case "running":
        return "●";
      case "queued":
      default:
        return "○";
    }
  };

  // Group events by run_id and get recent runs
  const recentEvents = events.slice(-50);

  return (
    <div className="relative z-50 pointer-events-none h-full w-full flex items-start justify-center pt-16">
      <div className="pointer-events-auto w-full max-w-3xl flex flex-col items-stretch">
        {/* Hero heading */}
        <div className="flex items-center gap-3 mb-6 px-2 select-none">
          <span className="text-[28px] font-semibold tracking-tight bg-gradient-to-r from-violet-400 via-fuchsia-400 to-sky-400 bg-clip-text text-transparent">
            orbit
          </span>
          <span className="inline-flex h-7 items-center gap-1 px-2 rounded-full bg-white/5 ring-1 ring-white/15">
            <span className="text-white/75 text-xs leading-none">@</span>
            <img src="/orbit-badge.svg" alt="Orbit badge" className="h-4 w-4 text-white animate-orbit-badge" />
          </span>
        </div>

        {/* Command Bar - large input */}
        <form
          onSubmit={handleSubmit}
          className={`orbit-capsule orbit-border-gradient orbit-shadow relative flex items-center gap-4 h-16 px-5 w-full backdrop-blur-2xl ${
            isFocused || isLoading ? "orbit-glow-active" : ""
          }`}
        >
          {/* Thin animated top sheen while loading */}
          {isLoading && <div className="progress-sheen" />}

          {/* Left icon: magnifier style */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="w-5 h-5 text-white/80"
            aria-hidden
          >
            <path d="M10 2a8 8 0 105.293 14.293l4.707 4.707 1.414-1.414-4.707-4.707A8 8 0 0010 2zm0 2a6 6 0 110 12A6 6 0 0110 4z" />
          </svg>

          {/* Input with idle hint overlay */}
          <div className="relative flex-1">
            <div
              aria-hidden
              className={`pointer-events-none absolute left-0 top-1/2 -translate-y-1/2 text-white/70 text-[15px] truncate hint-rotator ${
                input.trim().length === 0 && !isFocused ? "hint-visible" : "hint-hidden"
              }`}
            >
              {idleHints[hintIndex]}
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask anything or type a command"
              disabled={isLoading}
              className="orbit-input w-full bg-transparent outline-none text-white placeholder-white/85 text-[15px] pl-0 caret-violet-300"
              autoFocus
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="text-white/90 hover:text-white disabled:opacity-50 transition-opacity p-1"
            title="Run command"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white/80 rounded-full animate-spin" />
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path d="M3 12h14l-4.5 4.5 1.4 1.4L21.2 11l-7.3-6.9-1.4 1.4L17 10H3v2z" />
              </svg>
            )}
          </button>

          {/* Divider and steps toggle */}
          <div className="h-6 w-px bg-white/15 mx-1" />
          <button
            type="button"
            onClick={toggleSteps}
            className="text-white/80 hover:text-white transition-colors p-1"
            title="Toggle steps panel"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="w-5 h-5 text-white/85"
            >
              <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z" />
            </svg>
          </button>
        </form>

        {/* Steps Panel */}
        {isStepsOpen && (
          <div className="mt-4 w-full max-h-80 rounded-2xl border border-white/15 bg-black/75 backdrop-blur-xl p-4 overflow-hidden shadow-2xl animate-panel-in">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-white/90">Steps</h3>
              <button
                onClick={() => setIsStepsOpen(false)}
                className="text-white/60 hover:text-white/90 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {recentEvents.length === 0 ? (
                <p className="text-white/50 text-sm">No steps yet. Try running a command!</p>
              ) : (
                recentEvents.map((event, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                  >
                    <span className={`text-sm font-mono ${getStatusColor(event.status)}`}>
                      {getStatusIcon(event.status)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white/90 break-words">
                        {event.message}
                      </p>
                      {event.data && Object.keys(event.data).length > 0 && (
                        <details className="mt-1">
                          <summary className="text-xs text-white/60 cursor-pointer">
                            Details
                          </summary>
                          <pre className="text-xs text-white/70 mt-1 bg-black/30 p-2 rounded overflow-x-auto">
                            {JSON.stringify(event.data, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CommandBar;