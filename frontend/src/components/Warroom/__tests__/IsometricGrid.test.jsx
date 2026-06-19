import { render } from "@testing-library/react";
import IsometricGrid from "../IsometricGrid";

test("renders SVG grid", () => {
  const { container } = render(<IsometricGrid />);
  expect(container.querySelector("svg")).not.toBeNull();
});
