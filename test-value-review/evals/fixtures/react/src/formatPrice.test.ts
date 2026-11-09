import { expect, it } from "vitest";

import { formatPrice } from "./formatPrice";

it("is self-consistent", () => {
  expect(formatPrice(1234)).toBe(formatPrice(1234));
});

it("formats a hand-computed value", () => {
  expect(formatPrice(1234)).toBe("$12.34");
});
