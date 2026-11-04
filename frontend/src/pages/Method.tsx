import { Lbl } from '../components/ui'

export default function Method() {
  return (
    <div className="card method prose" style={{ maxWidth: 900 }}>
      <div className="sec-title">How this tracker is built</div>
      <h4>Sources, in order of precedence</h4>
      <p>Each manager's own website and portfolio page decides portfolio membership. Valuations, rounds and revenue come from company press releases and filings first, then PitchBook and Preqin news, Forbes, Bloomberg, Reuters, The Information, WSJ, FT and TechCrunch. Fund-level performance comes from public pension disclosures (CalPERS, UTIMCO, Washington State, Oregon PERS, Florida SBA and similar) where they exist.</p>
      <h4>Confidence labels</h4>
      <p><Lbl l="HARD" /> company or manager disclosure, filing or press release. <Lbl l="REPORTED" /> credible press reporting. <Lbl l="ESTIMATE" /> third-party estimate or extrapolation. Blank cells mean no figure could be verified; nothing is filled by guesswork.</p>
      <h4>Derived figures</h4>
      <p><b>Step-up</b> is the latest valuation divided by the earliest post-money in the company's recorded round history. A manager's <b>entry mark</b> is the post-money of the round in its first investment year (matched to the entry round where known), and <b>markup</b> is the latest valuation over that entry mark. Both are gross, company-level indicators, not fund returns: they ignore dilution, preference stacks, follow-on pricing and ownership. <b>Tracked managers</b> includes managers confirmed on the cap table through their portfolio page or round announcements, plus matches in the company's investor list.</p>
      <h4>Legacy exits and stale marks</h4>
      <p><b>Legacy exits</b> are holdings first backed before 2010 (or founded before 2005) that have since listed or been sold, such as Apple, Amazon or Alphabet. They stay in each manager's record but are hidden from the company list by default and left out of value totals, as are <b>stale</b> marks: old valuations with no current figure.</p>
      <h4>Coverage</h4>
      <p>The first build covers each manager's defining, largest and most recent positions rather than every logo on its site. Mega-funds list hundreds of companies, so coverage widens with each refresh. Public-company values are market capitalisation at the date shown.</p>
      <h4>Refresh cadence</h4>
      <p>A scheduled job runs every Monday. It re-verifies the most valuable and most recently funded companies, adds new rounds and new portfolio additions, updates market caps, fund raises and team changes, then pushes the snapshot to this site's API. Changes land in the Change Log.</p>
      <p className="note" style={{ marginTop: 14 }}>Not investment advice. Private-company figures are often unaudited and may lag; verify against primary documents before relying on any number for an investment decision.</p>
    </div>
  )
}
