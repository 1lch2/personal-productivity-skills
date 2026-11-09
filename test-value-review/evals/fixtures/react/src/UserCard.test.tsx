import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UserCard } from "./UserCard";

describe("UserCard", () => {
  it("renders the fixed name", () => {
    render(<UserCard user={{ name: "Alice", role: "Admin" }} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("renders two different names", () => {
    const { rerender } = render(<UserCard user={{ name: "Alice", role: "Admin" }} />);
    expect(screen.getByRole("heading", { name: "Alice" })).toBeInTheDocument();

    rerender(<UserCard user={{ name: "Bob", role: "Admin" }} />);
    expect(screen.getByRole("heading", { name: "Bob" })).toBeInTheDocument();
  });

  it("calls onSelect when clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<UserCard user={{ name: "Alice", role: "Admin" }} onSelect={onSelect} />);

    await user.click(screen.getByRole("button", { name: "Select" }));

    expect(onSelect).toHaveBeenCalled();
  });

  it("matches the snapshot", () => {
    const { container } = render(<UserCard user={{ name: "Alice", role: "Admin" }} />);
    expect(container).toMatchSnapshot();
  });
});
