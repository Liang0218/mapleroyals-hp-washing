import { JOB_PROFILES, type GainRange, type JobId, type JobProfile } from "./core/jobs";

const jobOrder: JobId[] = ["fighter", "page", "spearman", "bowman", "thief", "brawler", "gunslinger", "beginner"];
const jobNames: Record<JobId, string> = {
  fighter: "Hero", page: "Paladin", spearman: "Dark Knight", bowman: "Bowmaster / Marksman",
  thief: "Night Lord / Shadower", brawler: "Buccaneer", gunslinger: "Corsair", beginner: "Beginner",
};
function rangeText(range: GainRange): string {
  return range.low === range.high ? `${range.low}` : `${range.low}–${range.high} (平均 ${(range.low + range.high) / 2})`;
}
function jobbedMpRange(profile: JobProfile): GainRange {
  return profile.beginnerUntilLevel > 200 ? profile.levelupMpBeginner : profile.levelupMpJobbed;
}
function minMpFormula(profile: JobProfile): string {
  const slope = profile.minMp(2) - profile.minMp(1);
  const offset = profile.minMp(1) - slope;
  return `${slope} × 等級 ${offset < 0 ? "−" : "+"} ${Math.abs(offset)}`;
}
function skillNote(profile: JobProfile): string {
  if (!profile.maxhpSkill) return "—";
  const skill = profile.maxhpSkill;
  return `Improve MaxHP：每級技能升級 HP +${skill.levelupBonusPerLevel}、Method 1/2 +${skill.apBonusPerLevel}；最高 ${skill.maxLevel} 級（前置 ${skill.prereqSp} SP）`;
}
function advancesText(profile: JobProfile): string {
  if (profile.jobAdvances.size === 0) return "無轉職加成";
  return [...profile.jobAdvances.entries()].sort(([a], [b]) => a - b).map(([level, advance]) => {
    const { hpMid, mpMid, apBonus } = advance.spec;
    return `${level} 等（${advance.number} 轉）：HP +${hpMid}、MP +${mpMid}${apBonus ? `、AP +${apBonus}` : ""}`;
  }).join("；");
}

export function JobReference() {
  const profiles = jobOrder.map((job) => JOB_PROFILES[job]);
  return <section className="page-card job-reference-page">
    <div className="section-heading"><div><p className="eyebrow">Job reference</p><h2>職業洗血與成長數值</h2><p className="subheading">數值直接取自計算器使用的職業公式。範圍依 HP 模式不同而變；平均值模式會取範圍中點。</p></div></div>
    <div className="guide-note"><b>每 APR 增加 HP 怎麼看</b><p>Method 1：先用 Fresh AP 加 HP，再用 APR 洗血，把 AP 點回其他能力值；表格列出這次操作增加的 HP。Method 2：不需要 Fresh AP，直接用 APR 扣 MP 換 HP。兩種方式都會消耗 1 APR，扣除該職業表列的 MP。</p><p>MP wash 是消耗 1 APR 將 AP 點入 MP；每點增加的 MP 為表列職業範圍，再加上 ⌊base INT ÷ 10⌋。最小 MP 是洗血時不可低於的 base MP。</p></div>
    <div className="reference-table-wrap"><table className="reference-table">
      <thead><tr><th>職業</th><th>最小 MP 公式</th><th>200 等最小 MP</th><th>每 APR 扣 MP</th><th>每 APR 增加 HP<br />Method 1：用 Fresh AP 加 HP 後洗血</th><th>每 APR 增加 HP<br />Method 2：直接用 APR 洗血換 HP</th><th>MP wash 每點 AP 增加 MP</th><th>升級 HP（1–10 等）</th><th>升級 HP（11 等起）</th><th>升級 MP（11 等起）</th><th>技能加成</th></tr></thead>
      <tbody>{profiles.map((profile) => <tr key={profile.job}><th scope="row">{jobNames[profile.job]}</th><td>{minMpFormula(profile)}</td><td>{profile.minMp(200)}</td><td>{profile.mpRemovedPerApr}</td><td>{rangeText(profile.method1Base)}</td><td>{rangeText(profile.method2Base)}</td><td>{rangeText(profile.freshApMpBase)} + ⌊base INT ÷ 10⌋</td><td>{rangeText(profile.levelupHpBeginner)}</td><td>{rangeText(profile.levelupHpJobbed)}{profile.maxhpSkill ? ` + 技能等級 × ${profile.maxhpSkill.levelupBonusPerLevel}` : ""}</td><td>{rangeText(jobbedMpRange(profile))} + ⌊總 INT ÷ 10⌋</td><td>{skillNote(profile)}</td></tr>)}</tbody>
    </table></div>
    <h3 className="reference-subtitle">轉職時額外增加</h3>
    <p className="field-note">此表顯示計算器目前採用的轉職 HP／MP 固定值；3、4 轉的 AP 加成已列入。</p>
    <div className="reference-table-wrap"><table className="reference-advance-table"><thead><tr><th>職業</th><th>轉職等級與額外 HP／MP／AP</th></tr></thead><tbody>{profiles.map((profile) => <tr key={profile.job}><th scope="row">{jobNames[profile.job]}</th><td>{advancesText(profile)}</td></tr>)}</tbody></table></div>
    <p className="field-note">升級 MP 的實際增加量 = 表列職業基礎範圍 + ⌊總 INT ÷ 10⌋；總 INT 會計入裝備 INT 與 Maple Warrior。Improve MaxHP 技能效果會依技能等級套用，升級 HP 加成與洗血 HP 加成分別列出。</p>
  </section>;
}
