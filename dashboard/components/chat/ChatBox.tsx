"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { streamGroupChat, streamDirectChat, type ChatMessage as ChatMsg } from "@/lib/chatClient";
import { EventBus, EVENTS } from "@/lib/EventBus";
import ChatContactList from "./ChatContactList";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

const AGENT_NAMES: Record<string, string> = {
  strategist: "Jing",
  analyst: "Joe",
  critic: "James",
  onchain: "Jade",
  risk: "Jeed",
  engine: "Jai",
};

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function ChatBox({ visible, onClose }: Props) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const msgIdRef = useRef(0);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const addMessage = useCallback(
    (msg: Omit<ChatMsg, "id" | "timestamp">) => {
      const id = `msg-${++msgIdRef.current}`;
      setMessages((prev) => [
        ...prev,
        { ...msg, id, timestamp: new Date().toISOString() },
      ]);
      return id;
    },
    []
  );

  const updateMessage = useCallback((id: string, update: Partial<ChatMsg>) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...update } : m))
    );
  }, []);

  const handleSend = useCallback(
    async (text: string) => {
      // Add user message
      addMessage({ role: "user", content: text });
      setStreaming(true);

      // Create placeholder for agent response
      const agentId = selectedAgent || "strategist";
      const responseId = addMessage({
        role: "agent",
        agentId,
        content: "",
        streaming: true,
      });

      let fullContent = "";

      try {
        const stream = selectedAgent
          ? streamDirectChat(selectedAgent, text)
          : streamGroupChat(text);

        for await (const event of stream) {
          if (event.event === "message" && event.data.content) {
            fullContent += event.data.content;
            updateMessage(responseId, {
              content: fullContent,
              agentId: event.data.agent_id || agentId,
            });

            // Update Phaser bubble
            EventBus.emit(
              EVENTS.AGENT_BUBBLE,
              event.data.agent_id || agentId,
              fullContent.slice(-80)
            );
          }

          if (event.event === "agent-move") {
            EventBus.emit(
              EVENTS.AGENT_MOVE,
              event.data.agent_id,
              event.data.room
            );
          }

          if (event.event === "error") {
            updateMessage(responseId, {
              content: `❌ ${event.data.message}`,
              streaming: false,
            });
            break;
          }

          if (event.event === "done") {
            break;
          }
        }
      } catch (err: any) {
        updateMessage(responseId, {
          content: `❌ ${err.message || "Stream error"}`,
        });
      }

      updateMessage(responseId, { streaming: false });
      setStreaming(false);
    },
    [selectedAgent, addMessage, updateMessage]
  );

  if (!visible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: -300, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: -300, opacity: 0 }}
        transition={{ type: "spring", damping: 25, stiffness: 250 }}
        className="fixed left-0 top-0 bottom-0 z-40 flex"
        style={{ width: 380 }}
      >
        {/* Chat panel */}
        <div className="flex-1 flex flex-col bg-gray-900/95 backdrop-blur-sm border-r border-gray-700">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-700">
            <div className="flex items-center gap-2">
              <span className="text-sm">💬</span>
              <span className="text-[10px] font-bold text-gray-200">
                {selectedAgent
                  ? `DM: ${AGENT_NAMES[selectedAgent] || selectedAgent}`
                  : "Group Chat"}
              </span>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-300 text-xs"
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="flex flex-1 overflow-hidden">
            {/* Contact list */}
            <ChatContactList
              selected={selectedAgent}
              onSelect={setSelectedAgent}
            />

            {/* Messages */}
            <div className="flex-1 flex flex-col">
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-3 space-y-1"
              >
                {messages.length === 0 && (
                  <div className="text-center text-gray-500 text-[10px] mt-8">
                    <div className="text-2xl mb-2">💬</div>
                    <div>
                      {selectedAgent
                        ? `Send a message to ${AGENT_NAMES[selectedAgent]}`
                        : "Ask the trading team anything"}
                    </div>
                  </div>
                )}
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} msg={msg} />
                ))}
              </div>

              {/* Input */}
              <ChatInput
                onSend={handleSend}
                disabled={streaming}
                agentName={
                  selectedAgent
                    ? AGENT_NAMES[selectedAgent] || selectedAgent
                    : undefined
                }
              />
            </div>
          </div>
        </div>

        {/* Drag handle */}
        <div className="w-1 bg-gray-700 hover:bg-blue-500 cursor-col-resize transition-colors" />
      </motion.div>
    </AnimatePresence>
  );
}
