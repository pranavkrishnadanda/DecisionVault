import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SlackIntegrationPageClient } from "@/ui/features/slack/slack-integration-page-client";

const mockUseSearchParams = vi.fn();
const mockUseSlackIntegrationsQuery = vi.fn();
const mockUseSlackChannelsQuery = vi.fn();
const mockUseSlackMessagesQuery = vi.fn();
const mockUseSlackTestMutation = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => mockUseSearchParams(),
}));

vi.mock("@/hooks/use-slack-query", () => ({
  useSlackIntegrationsQuery: (...args: unknown[]) =>
    mockUseSlackIntegrationsQuery(...args),
  useSlackChannelsQuery: (...args: unknown[]) =>
    mockUseSlackChannelsQuery(...args),
  useSlackMessagesQuery: (...args: unknown[]) =>
    mockUseSlackMessagesQuery(...args),
  useSlackTestMutation: (...args: unknown[]) =>
    mockUseSlackTestMutation(...args),
}));

describe("Slack integration page", () => {
  beforeEach(() => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams());

    mockUseSlackIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
    });
    mockUseSlackMessagesQuery.mockReturnValue({
      data: { messages: [], has_more: false, next_cursor: "" },
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackTestMutation.mockReturnValue({
      mutateAsync: vi
        .fn()
        .mockResolvedValue({ success: true, message_ts: "1.2", error: null }),
      isPending: false,
    });
  });

  it("renders Add Slack and redirects to install", () => {
    render(<SlackIntegrationPageClient />);

    expect(screen.getByRole("link", { name: /add slack/i })).toHaveAttribute(
      "href",
      "/api/slack/install",
    );
  });

  it("shows connected state and fetches channels on success return", () => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams("status=success"));
    mockUseSlackIntegrationsQuery.mockReturnValue({
      data: [{ id: "int-1", team_name: "Acme Workspace" }],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [
        {
          id: "C1",
          name: "general",
          is_private: false,
          num_members: 12,
          topic: "ops",
        },
      ],
      isPending: false,
      isError: false,
    });

    render(<SlackIntegrationPageClient />);

    expect(
      screen.getByText(/connected to acme workspace/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/channel/i)).toBeInTheDocument();
  });

  it("shows error state with retry", () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("status=error&reason=invalid_state"),
    );

    render(<SlackIntegrationPageClient />);

    expect(screen.getByText(/slack connection failed/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("renders private channels with lock icon", () => {
    mockUseSlackIntegrationsQuery.mockReturnValue({
      data: [{ id: "int-1", team_name: "Acme Workspace" }],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [
        {
          id: "C1",
          name: "general",
          is_private: false,
          num_members: 12,
          topic: "ops",
        },
        {
          id: "G1",
          name: "leadership",
          is_private: true,
          num_members: 3,
          topic: "exec",
        },
      ],
      isPending: false,
      isError: false,
    });

    render(<SlackIntegrationPageClient />);

    expect(
      screen.getByRole("option", { name: /general/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /🔒 leadership/i }),
    ).toBeInTheDocument();
  });

  it("renders messages with names, threads, and paginates", async () => {
    mockUseSlackIntegrationsQuery.mockReturnValue({
      data: [{ id: "int-1", team_name: "Acme Workspace" }],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [
        {
          id: "C1",
          name: "general",
          is_private: false,
          num_members: 12,
          topic: "ops",
        },
      ],
      isPending: false,
      isError: false,
    });

    const messagesHookCalls: unknown[][] = [];
    mockUseSlackMessagesQuery.mockImplementation((...args: unknown[]) => {
      messagesHookCalls.push(args);
      const cursor = args[2] as string;
      if (cursor === "cursor-2") {
        return {
          data: {
            messages: [
              {
                user_name: "Bob",
                text: "Older",
                ts: "120",
                thread_replies: [],
              },
            ],
            has_more: false,
            next_cursor: "",
          },
          isPending: false,
          isError: false,
          refetch: vi.fn(),
        };
      }
      return {
        data: {
          messages: [
            {
              user_name: "Alice",
              text: "Hello",
              ts: "123",
              thread_replies: [{ user_name: "Bob", text: "Reply", ts: "124" }],
            },
          ],
          has_more: true,
          next_cursor: "cursor-2",
        },
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      };
    });

    render(<SlackIntegrationPageClient />);

    fireEvent.change(screen.getByLabelText(/channel/i), {
      target: { value: "C1" },
    });

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText(/thread \(1\)/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /load more/i }));

    await waitFor(() => {
      expect(messagesHookCalls.some((call) => call[2] === "cursor-2")).toBe(
        true,
      );
    });
  });
});
