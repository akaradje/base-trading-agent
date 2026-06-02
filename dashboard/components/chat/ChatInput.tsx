"use client";

import { useState, useRef, useEffect } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  agentName?: string;
}

export default function ChatInput({ onSend, disabled, agentName }: Props) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [agentName]);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-700 p-2">
      {agentName && (
        <div className="text-[9px] text-gray-500 mb-1 px-1">
          Chatting with <span className="text-gray-300">{agentName}</span>
        </div>
      )}
      <div className="flex gap-2">
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={agentName ? `Message ${agentName}...` : "Ask the team..."}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-gray-800/60 border border-gray-600 rounded px-2 py-1.5 text-xs text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500/50 disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="px-3 py-1.5 bg-blue-600/30 border border-blue-500/30 rounded text-xs text-blue-300 hover:bg-blue-600/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          ➤
        </button>
      </div>
    </div>
  );
}
