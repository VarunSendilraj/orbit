import React, { useEffect, useMemo, useState } from "react";
import { connectSteps, runCommand, StepEvent } from "../lib/steps";
import { ChatContainerRoot, ChatContainerContent } from "@/components/prompt-kit/chat-container";
import { Message, MessageAvatar, MessageContent } from "@/components/prompt-kit/message";
import { PromptInput, PromptInputActions, PromptInputTextarea } from "@/components/prompt-kit/prompt-input";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";

const Chat: React.FC = () => {
  type ChatMessage = { id: string; role: "user" | "assistant"; content: string };
  const [events, setEvents] = useState<StepEvent[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [composer, setComposer] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [open, setOpen] = useState(true);
  const [runMessageMap, setRunMessageMap] = useState<Record<string, string>>({});

  useEffect(() => {
    const ws = connectSteps((evt) => {
      setEvents((prev) => [...prev, evt]);
      setMessages((prev) => {
        const messageId = runMessageMap[evt.run_id];
        if (!messageId) return prev;
        return prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                content: `${m.content}${m.content ? "\n" : ""}[${evt.status.toUpperCase()}] ${evt.message}`,
              }
            : m
        );
      });
    });
    return () => ws.close();
  }, [runMessageMap]);

  const recent = useMemo(() => events.slice(-200), [events]);

  const handleSubmit = async () => {
    const content = composer.trim();
    if (!content || isLoading) return;
    setMessages((m) => [...m, { id: crypto.randomUUID(), role: "user", content }]);
    setComposer("");
    setIsLoading(true);
    try {
      const res = await runCommand(content);
      const runId: string | undefined = res?.run_id;
      const assistantId = crypto.randomUUID();
      setMessages((m) => [
        ...m,
        {
          id: assistantId,
          role: "assistant",
          content: "Planning…",
        },
      ]);
      if (runId) {
        setRunMessageMap((map) => ({ ...map, [runId]: assistantId }));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full w-full grid grid-cols-1 md:grid-cols-[1fr_380px]">
      <div className="relative">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-black/30 backdrop-blur">
          <div className="flex items-center gap-2 select-none">
            <img src="/orbit-badge.svg" alt="Orbit" className="h-5 w-5 animate-orbit-badge" />
            <span className="font-semibold text-white bg-gradient-to-r from-violet-300 via-fuchsia-300 to-sky-300 bg-clip-text text-transparent">orbit</span>
            <Badge variant="secondary" className="ml-2">Alpha</Badge>
          </div>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger className="text-sm text-white/80 hover:text-white">Steps</SheetTrigger>
            <SheetContent side="right" className="w-[380px] bg-black text-white">
              <SheetHeader>
                <SheetTitle>Execution steps</SheetTitle>
              </SheetHeader>
              <Separator className="my-3 bg-white/10" />
              <ScrollArea className="h-[calc(100vh-7rem)] pr-2">
                <div className="space-y-2">
                  {recent.length === 0 ? (
                    <div className="text-sm text-white/60">No steps yet. Run a command.</div>
                  ) : (
                    recent.map((e, i) => (
                      <div key={`${e.run_id}-${e.step_id}-${i}`} className="rounded-lg border border-white/10 p-2">
                        <div className="text-xs uppercase tracking-wide opacity-70">{e.status}</div>
                        <div className="text-sm">{e.message}</div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </SheetContent>
          </Sheet>
        </div>

        <div className="h-[calc(100%-48px)]">
          <ChatContainerRoot className="relative h-full">
            <ChatContainerContent className="space-y-6 px-4 py-6">
              {messages.length === 0 && (
                <div className="text-white/60 text-sm">Ask Orbit to do something. Examples: "Open app: Safari", "Run tests", "Search files: build.sh"</div>
              )}

              {messages.map((m) => (
                <Message
                  key={m.id}
                  className={
                    m.role === "user"
                      ? "mx-auto w-full max-w-3xl flex items-end justify-end gap-2 px-2 md:px-10"
                      : "mx-auto w-full max-w-3xl flex items-start gap-2 px-2 md:px-10"
                  }
                >
                  {m.role === "assistant" && (
                    <MessageAvatar src="/orbit-badge.svg" alt="Orbit" fallback="O" />
                  )}
                  <MessageContent
                    className={
                      m.role === "user"
                        ? "bg-muted text-primary max-w-[85%] rounded-3xl px-5 py-2.5 whitespace-pre-wrap sm:max-w-[75%]"
                        : "text-foreground prose w-full min-w-0 flex-1 rounded-lg bg-transparent p-0 text-sm whitespace-pre-wrap"
                    }
                  >
                    {m.content}
                  </MessageContent>
                </Message>
              ))}

              {recent.length > 0 && (
                <div className="space-y-2">
                  {recent.map((evt, idx) => (
                    <div key={`${evt.run_id}-${evt.step_id}-${idx}`} className="mx-auto w-full max-w-3xl px-2 md:px-10">
                      <div className="text-foreground prose w-full min-w-0 rounded-lg bg-transparent p-0 text-sm">
                        <span className="opacity-70 mr-2 uppercase">{evt.status}</span>
                        {evt.message}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ChatContainerContent>
          </ChatContainerRoot>

          <div className="inset-x-0 bottom-0 mx-auto w-full max-w-3xl shrink-0 px-3 pb-3 md:px-5 md:pb-5">
            <PromptInput
              isLoading={isLoading}
              value={composer}
              onValueChange={setComposer}
              onSubmit={handleSubmit}
              className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-xs"
            >
              <div className="flex flex-col">
                <PromptInputTextarea
                  placeholder="Ask anything or type a command"
                  className="min-h-[44px] pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit();
                    }
                  }}
                />

                <PromptInputActions className="mt-3 flex w-full items-center justify-between gap-2 p-2">
                  <div />
                  <div className="flex items-center gap-2">
                    <Button
                      size="icon"
                      disabled={!composer.trim() || isLoading}
                      onClick={handleSubmit}
                      className="size-9 rounded-full"
                    >
                      {isLoading ? <span className="size-3 rounded-xs bg-white" /> : <span>↩</span>}
                    </Button>
                  </div>
                </PromptInputActions>
              </div>
            </PromptInput>
          </div>
        </div>
      </div>

      <div className="hidden md:flex flex-col border-l border-white/10 bg-black/40">
        <div className="px-4 py-2 text-sm text-white/70">Steps</div>
        <Separator className="bg-white/10" />
        <ScrollArea className="flex-1 p-3">
          <div className="space-y-2">
            {recent.length === 0 ? (
              <div className="text-sm text-white/60">No steps yet. Run a command.</div>
            ) : (
              recent.map((e, i) => (
                <div key={`${e.run_id}-${e.step_id}-${i}`} className="rounded-lg border border-white/10 p-2">
                  <div className="text-xs uppercase tracking-wide opacity-70">{e.status}</div>
                  <div className="text-sm">{e.message}</div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
};

export default Chat;


