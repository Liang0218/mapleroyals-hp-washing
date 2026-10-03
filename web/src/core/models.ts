/** Shared, UI-independent types. Keep these field names aligned with Python core.models. */
export type PolicyName =
  | "mp_wash_shortfall"
  | "int_dump_shortfall"
  | "mp_wash_hardcore"
  | "int_only_plain";

export type HpMode = "avg" | "min" | "max";

export type Action =
  | "NONE" | "BUILD" | "HP1" | "HP2" | "HP3" | "HP4" | "HP5"
  | "MP1" | "MP2" | "MP3" | "MP4" | "MP5" | "HARDCORE_GREEDY"
  | "INT5" | "LUK5" | "STR5" | "DEX5" | "M2" | "RESET_INT" | "RESUME";

export interface IntGearSegment {
  from_level: number;
  to_level: number;
  int_gear: number;
}

export interface EquipmentItem {
  name: string;
  type: EquipmentType;
  int: number;
  equip_level: number;
}

export const EQUIPMENT_TYPES = [
  "Hat", "Face Accessory", "Eye Accessory", "Earring", "Pendant", "Medal",
  "Shoulder", "Overall", "Cape", "Belt", "Glove", "Weapon", "Shield", "Ring", "Shoe",
] as const;
export type EquipmentType = (typeof EQUIPMENT_TYPES)[number];

export interface ResumeFrom {
  level: number;
  base_hp: number;
  base_mp: number;
  base_int: number;
  base_luk?: number;
  base_dex?: number;
  base_str?: number;
  fresh_ap?: number;
  int_reset_done?: boolean;
  base_int_peak?: number;
}

export interface SimulateConfig {
  policy: PolicyName;
  target_base_int: number;
  target_hp: number;
  int_reset_level: number;
  int_gear: IntGearSegment[];
  job?: string;
  mp_wash_end?: number;
  extra_mp_threshold?: number;
  quest_equip_hp?: number;
  hp_mode?: HpMode;
  max_level?: number;
  auto_method2?: boolean;
  mw_percent?: number;
  mw_from_level?: number;
  int_gear_after_reset?: number;
  resume_from?: ResumeFrom;
  improved_maxhp_level?: number;
  target_mp?: number;
}

export interface OptimizeConfig {
  target_hp: number;
  int_reset_level: number;
  int_gear: IntGearSegment[];
  job?: string;
  policies?: PolicyName[];
  quest_equip_hp?: number;
  hp_mode?: HpMode;
  max_level?: number;
  mw_percent?: number;
  mw_from_level?: number;
  int_gear_after_reset?: number;
  extra_mp_threshold?: number;
  target_base_int_min?: number;
  target_base_int_max?: number;
  target_base_int_step?: number;
  mp_wash_end_min?: number;
  top_n?: number;
  resume_from?: ResumeFrom;
  improved_maxhp_level?: number;
  target_mp?: number;
}

export interface AprBreakdown {
  mp_wash_count: number;
  method1_hp_wash_count: number;
  method2_hp_wash_count: number;
  int_reset_apr: number;
}

export interface LevelPlanRow {
  level: number;
  action: Action;
  base_int: number;
  base_luk: number;
  base_hp: number;
  base_mp: number;
  extra_mp: number;
  fresh_ap_int: number;
  fresh_ap_luk: number;
  fresh_ap_dex: number;
  fresh_ap_str: number;
  fresh_ap_hp: number;
  fresh_ap_mp: number;
  apr_spent: number;
  notes: string;
}

export interface SimulateResult {
  policy: PolicyName;
  target_base_int: number;
  target_hp: number;
  int_reached_level: number;
  mp_wash_end: number;
  extra_mp_threshold: number;
  int_gear_after_reset: number;
  final_base_hp: number;
  final_display_hp: number;
  final_base_mp: number;
  base_int_peak: number;
  reached_target: boolean;
  apr: AprBreakdown;
  plan: LevelPlanRow[];
  resume_from?: ResumeFrom;
  job: string;
  improved_maxhp_level?: number;
  target_mp?: number;
}

export interface CandidateResult extends SimulateResult {}

export interface PolicyBest { policy: PolicyName; best?: CandidateResult; top: CandidateResult[]; }
export interface ComparisonResult {
  policy_a?: CandidateResult; policy_b?: CandidateResult; policy_c?: CandidateResult; policy_d?: CandidateResult;
  winner?: CandidateResult; apr_delta?: number; hp_delta?: number;
}
export interface OptimizeResult {
  by_policy: Partial<Record<PolicyName, PolicyBest>>;
  comparison: ComparisonResult;
  winner?: CandidateResult;
  top_candidates: CandidateResult[];
  resume_from?: ResumeFrom;
}

export const totalApr = (apr: AprBreakdown): number =>
  apr.mp_wash_count + apr.method1_hp_wash_count + apr.method2_hp_wash_count + apr.int_reset_apr;
