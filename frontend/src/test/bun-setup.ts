import { createRequire } from "node:module";
import "@testing-library/jest-dom/vitest";
import { JSDOM } from "jsdom";
import { afterEach, vi } from "vitest";

const dom = new JSDOM("<!doctype html><html><body></body></html>", {
  url: "http://localhost/",
});

const globalObject = globalThis as Record<string, unknown>;
const windowObject = dom.window as unknown as Record<string, unknown>;

globalObject.window = dom.window;
globalObject.document = dom.window.document;
globalObject.navigator = dom.window.navigator;
globalObject.HTMLElement = dom.window.HTMLElement;
globalObject.Node = dom.window.Node;
globalObject.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
globalObject.MutationObserver = dom.window.MutationObserver;

for (const key of Object.getOwnPropertyNames(windowObject)) {
  if (key in globalObject) {
    continue;
  }
  globalObject[key] = windowObject[key];
}

const originalGlobals = new Map<string, PropertyDescriptor | undefined>();

if (!("mocked" in vi)) {
  (vi as unknown as { mocked: <T>(value: T) => T }).mocked = <T>(value: T) =>
    value;
}

if (!("stubGlobal" in vi)) {
  (
    vi as unknown as {
      stubGlobal: (name: string, value: unknown) => void;
    }
  ).stubGlobal = (name: string, value: unknown) => {
    if (!originalGlobals.has(name)) {
      originalGlobals.set(
        name,
        Object.getOwnPropertyDescriptor(globalThis, name),
      );
    }
    Object.defineProperty(globalThis, name, {
      value,
      writable: true,
      configurable: true,
    });
  };
}

if (!("unstubAllGlobals" in vi)) {
  (vi as unknown as { unstubAllGlobals: () => void }).unstubAllGlobals = () => {
    for (const [name, descriptor] of originalGlobals.entries()) {
      if (!descriptor) {
        delete globalObject[name];
        continue;
      }
      Object.defineProperty(globalThis, name, descriptor);
    }
    originalGlobals.clear();
  };
}

const require = createRequire(import.meta.url);
const { cleanup } = require("@testing-library/react") as {
  cleanup: () => void;
};

afterEach(() => {
  cleanup();
});
