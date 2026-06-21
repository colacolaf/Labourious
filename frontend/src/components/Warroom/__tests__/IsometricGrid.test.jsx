import { render } from "@testing-library/react";
import IsometricGrid from "../IsometricGrid";

test("renders SVG grid", () => {
  const { baseElement } = render(<IsometricGrid />);
  // eslint-disable-next-line testing-library/no-node-access
  expect(baseElement.querySelector("svg")).not.toBeNull();
});
