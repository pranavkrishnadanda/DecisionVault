"use client";

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import {
  useSlackChannelsQuery,
  useSlackIntegrationsQuery,
  useSlackMessagesQuery,
  useSlackTestMutation,
} from "@/hooks/use-slack-query";

export function SlackIntegrationPageClient() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");
  const reason = searchParams.get("reason");

  const integrationsQuery = useSlackIntegrationsQuery();
  const integration = integrationsQuery.data?.[0] ?? null;

  const [selectedChannelId, setSelectedChannelId] = useState("");
  const [messageCursor, setMessageCursor] = useState("");
  const [testFeedback, setTestFeedback] = useState<string>("");

  const channelsQuery = useSlackChannelsQuery(
    integration?.id ?? "",
    Boolean(integration),
  );
  const messagesQuery = useSlackMessagesQuery(
    integration?.id ?? "",
    selectedChannelId,
    messageCursor,
    Boolean(integration),
  );
  const slackTestMutation = useSlackTestMutation();

  const connectionState = useMemo(() => {
    if (status === "error") {
      return "error" as const;
    }
    if (!integration) {
      return "not_connected" as const;
    }
    return "connected" as const;
  }, [integration, status]);

  const messages = messagesQuery.data?.messages ?? [];

  async function handleSendTest() {
    if (!integration || selectedChannelId.trim().length === 0) {
      return;
    }
    const result = await slackTestMutation.mutateAsync({
      integrationId: integration.id,
      channelId: selectedChannelId,
    });
    if (result.success) {
      setTestFeedback("Test sent successfully");
      return;
    }
    setTestFeedback(`Test failed: ${result.error ?? "unknown_error"}`);
  }

  if (connectionState === "error") {
    return (
      <section className="rounded-xl border border-rose-300 bg-rose-50 p-6">
        <h2 className="text-lg font-semibold text-rose-900">
          Slack connection failed
        </h2>
        <p className="mt-1 text-sm text-rose-800">
          Reason: {reason ?? "unknown_error"}
        </p>
        <button
          className="mt-4 rounded-md border border-rose-300 bg-white px-3 py-2 text-sm"
          onClick={() => {
            window.location.assign("/api/slack/install");
          }}
          type="button"
        >
          Retry
        </button>
      </section>
    );
  }

  if (connectionState === "not_connected") {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">
          Slack Integration
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Connect your workspace to read channel history and send test messages.
        </p>
        <a
          className="mt-4 inline-block rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
          href="/api/slack/install"
        >
          Add Slack
        </a>
      </section>
    );
  }

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">
          Connected to {integration.team_name}
        </h2>
      </header>

      <div>
        <label
          className="mb-1 block text-sm text-slate-700"
          htmlFor="slack-channel-select"
        >
          Channel
        </label>
        <select
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          id="slack-channel-select"
          onChange={(event) => {
            setSelectedChannelId(event.target.value);
            setMessageCursor("");
          }}
          value={selectedChannelId}
        >
          <option value="">Select channel</option>
          {(channelsQuery.data ?? []).map((channel) => (
            <option key={channel.id} value={channel.id}>
              {channel.is_private ? "🔒 " : ""}
              {channel.name} ({channel.num_members})
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <button
          className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:opacity-50"
          disabled={
            selectedChannelId.trim().length === 0 || slackTestMutation.isPending
          }
          onClick={() => {
            void handleSendTest();
          }}
          type="button"
        >
          {slackTestMutation.isPending ? "Testing..." : "Send Test"}
        </button>
        {testFeedback && (
          <p className="text-sm text-slate-700">{testFeedback}</p>
        )}
      </div>

      <section className="space-y-3">
        {messages.map((message) => (
          <article
            className="rounded-lg border border-slate-200 p-3"
            key={message.ts}
          >
            <p className="text-sm font-semibold text-slate-900">
              {message.user_name}
            </p>
            <p className="text-sm text-slate-700">{message.text}</p>
            {message.thread_replies.length > 0 && (
              <div className="mt-2 rounded-md bg-slate-50 p-2">
                <p className="text-xs font-medium text-slate-600">
                  Thread ({message.thread_replies.length})
                </p>
                {message.thread_replies.map((reply) => (
                  <p className="text-xs text-slate-700" key={reply.ts}>
                    <span className="font-medium">{reply.user_name}:</span>{" "}
                    {reply.text}
                  </p>
                ))}
              </div>
            )}
          </article>
        ))}

        {messagesQuery.data?.has_more && (
          <button
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            onClick={() => {
              setMessageCursor(messagesQuery.data?.next_cursor ?? "");
            }}
            type="button"
          >
            Load more
          </button>
        )}
      </section>
    </section>
  );
}
