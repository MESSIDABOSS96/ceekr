"use client";

import type { ChatMessage } from "@/lib/types";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] whitespace-pre-line rounded-2xl px-4 py-2.5 text-[0.88rem] leading-relaxed ${
          isUser
            ? "bg-twitter/15 text-text-primary"
            : "bg-surface-card text-text-body"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
