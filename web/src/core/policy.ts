import type { Action, PolicyName } from "./models";

export const HARDCORE_EARLY_START_LEVEL = 10;
export const HARDCORE_MP_WASH_MIN_LEVEL = 30;

export function chooseEarlyAction(policy: PolicyName, extraMp: number, threshold: number): Action {
  if (policy === "mp_wash_hardcore") return "HARDCORE_GREEDY";
  if (policy === "mp_wash_shortfall") return extraMp >= threshold ? "HP5" : "MP5";
  if (policy === "int_dump_shortfall") return extraMp >= threshold ? "HP5" : "INT5";
  if (policy === "int_only_plain") return "INT5";
  throw new Error("unknown policy");
}
