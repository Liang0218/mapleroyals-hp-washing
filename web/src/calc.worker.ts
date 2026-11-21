/// <reference lib="webworker" />
import { optimize } from "./core/optimizer";
import { simulate } from "./core/simulator";

export type CalcRequest =
  | { kind: "optimize"; params: Parameters<typeof optimize>[0] }
  | { kind: "simulate"; params: Parameters<typeof simulate>[0] };
export type CalcResponse =
  | { ok: true; result: ReturnType<typeof optimize> | ReturnType<typeof simulate> }
  | { ok: false; message: string };

// Runs the heavy search off the main thread so the page stays responsive and can be cancelled.
self.onmessage = (event: MessageEvent<CalcRequest>) => {
  try {
    const request = event.data;
    const result = request.kind === "optimize" ? optimize(request.params) : simulate(request.params);
    self.postMessage({ ok: true, result } satisfies CalcResponse);
  } catch (error) {
    self.postMessage({ ok: false, message: error instanceof Error ? error.message : String(error) } satisfies CalcResponse);
  }
};
