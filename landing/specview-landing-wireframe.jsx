import { useState, useEffect } from "react";

const DOCS = [
  { icon: "🔍", name: "Analysis", desc: "Problem · constraints · scope · open questions" },
  { icon: "🎯", name: "Epic", desc: "Tasks · effort · dependencies · success criteria" },
  { icon: "🏗️", name: "Architecture", desc: "Design · decisions · tradeoffs · stack" },
  { icon: "📅", name: "Timeline", desc: "Status · progress · phase gates" },
  { icon: "🛠️", name: "Implementation Guide", desc: "Steps · files · tests · commit plan · rollback" },
];

const METRICS = [
  { value: "764+", label: "tests passing" },
  { value: "433", label: "commits" },
  { value: "44.5s", label: "generation time" },
  { value: "0", label: "human code lines" },
];

const COMPARE = [
  { dim: "Input", them: "Chat prompt", us: "Brain dump (3 paragraphs)" },
  { dim: "Output", them: "Code you didn't write", us: "Specs you review + code that matches" },
  { dim: "Architecture", them: "AI decides", us: "You review before code is written" },
  { dim: "Documentation", them: "None", us: "Built-in — every feature is documented" },
  { dim: "Quality signal", them: "Hope it works", us: "Deviation tracking + correction loop" },
  { dim: "Pricing", them: "$20-550/mo credits", us: "$29/mo flat, unlimited" },
];

const STEPS = [
  {
    num: "1",
    title: "Braindump",
    desc: "Write everything you know about the feature — raw, unfiltered, unstructured. The messier the better.",
    example: `We need a billing system. Stripe. Free tier = 3 projects/month, Pro = unlimited at $29/mo. Usage tracking per user. Webhook for checkout.completed. Don't overbuild — no annual plans, no team seats, no invoicing. Just works.`,
  },
  {
    num: "2",
    title: "Generate",
    desc: "One click. The AI chain runs: analysis → epic → architecture → timeline → implementation guide. Each file appears as it completes.",
    example: `✦ analysis ████████████ done  (12.3s)
✦ epic     ████████████ done  (18.1s)  
✦ arch     ████████████ done  (31.7s)
✦ timeline ████████████ done  (2.1s)
✦ impl     ████░░░░░░░░ ...   (44.5s)
5 files · claude-sonnet · generating...`,
  },
  {
    num: "3",
    title: "Read & Build",
    desc: "Open the specs in Specview. Read them like a newspaper. Hand the implementation guide to Claude Code. Every task has file paths, test bodies, and a commit plan.",
    example: `Task 1: Wire Stripe Adapter
├─ Files: billing/adapter.py (new), billing/service.py (new)
├─ Tests: 7 assertions, full bodies
├─ Commit: "feat(billing): wire Stripe checkout + webhook"
└─ Verify: pytest tests/test_billing.py — 7 passed`,
  },
];

const TESTIMONIALS = [
  {
    quote: "I wrote 3 paragraphs about a feature. 47 seconds later I had an analysis, an epic, an architecture doc, and an implementation guide with test bodies. Human code lines written: 0.",
    author: "What using Spec Doc feels like",
  },
  {
    quote: "The agent that loads conventions before writing code cannot bypass the adapter boundary, because the rule is in its context — not its memory.",
    author: "Why conventions compound",
  },
];

const FAQ = [
  {
    q: "What do I need to use Specview?",
    a: "A browser. Sign up, paste a brain dump, click generate. The hosted version runs everything — no CLI, no local setup, no API key needed.",
  },
  {
    q: "Is this like Lovable or Bolt?",
    a: "No. Lovable generates code from prompts. Specview generates specs from brain dumps. You review the architecture before any code is written. The specs become the documentation.",
  },
  {
    q: "What if the generated specs are wrong?",
    a: "Edit the brain dump and regenerate. Or edit the markdown directly. The specs are files you own — not locked in a platform.",
  },
  {
    q: "Can I self-host?",
    a: "Yes. Specview is open-source. git clone, docker compose up, done. The hosted version at specview.dev saves you the setup.",
  },
  {
    q: "Why $29/month?",
    a: "Unlimited spec generation. No credits. No per-request charges. Kiro costs $20-550/month in credits. Cursor is $20/month for code suggestions. $29/month for full architecture documents is a different category of value.",
  },
];

export default function SpecviewLanding() {
  const [openFaq, setOpenFaq] = useState(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const sectionStyle = {
    maxWidth: 860,
    margin: "0 auto",
    padding: "0 24px",
  };

  return (
    <div style={{
      background: "#FFFEF9",
      color: "#121212",
      fontFamily: "'Source Serif 4', 'Georgia', serif",
      minHeight: "100vh",
      lineHeight: 1.7,
    }}>
      {/* NAV */}
      <nav style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        background: scrolled ? "rgba(255,254,249,0.97)" : "#FFFEF9",
        borderBottom: scrolled ? "1px solid #121212" : "none",
        transition: "all 0.2s",
        padding: "12px 24px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        maxWidth: 860,
        margin: "0 auto",
      }}>
        <span style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: 18,
          fontWeight: 700,
          letterSpacing: "-0.02em",
        }}>
          Specview
        </span>
        <div style={{ display: "flex", gap: 24, fontSize: 13, fontFamily: "'Source Sans 3', sans-serif" }}>
          <a href="#what" style={{ color: "#121212", textDecoration: "none" }}>What</a>
          <a href="#how" style={{ color: "#121212", textDecoration: "none" }}>How</a>
          <a href="#pricing" style={{ color: "#121212", textDecoration: "none" }}>Pricing</a>
          <a href="https://specview.dev/signup" style={{
            color: "#FFFEF9",
            background: "#121212",
            padding: "6px 16px",
            textDecoration: "none",
            fontSize: 12,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
          }}>
            Try it free
          </a>
        </div>
      </nav>

      {/* MASTHEAD */}
      <header style={{
        ...sectionStyle,
        textAlign: "center",
        padding: "80px 24px 40px",
        borderBottom: "3px solid #121212",
      }}>
        <div style={{
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          color: "#888",
          fontFamily: "'Source Sans 3', sans-serif",
          marginBottom: 8,
        }}>
          {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
        </div>
        <h1 style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: 64,
          fontWeight: 900,
          letterSpacing: "-0.03em",
          lineHeight: 1.0,
          margin: "0 0 16px",
        }}>
          Specview
        </h1>
        <p style={{
          fontStyle: "italic",
          fontSize: 15,
          color: "#666",
          margin: 0,
        }}>
          All the Specs Fit to Build
        </p>
      </header>

      {/* HERO */}
      <section style={{
        ...sectionStyle,
        padding: "60px 24px",
        textAlign: "center",
      }}>
        <h2 style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: 36,
          fontWeight: 700,
          lineHeight: 1.2,
          margin: "0 0 20px",
          maxWidth: 640,
          marginLeft: "auto",
          marginRight: "auto",
        }}>
          Your brain dump becomes an engineering spec in minutes.
        </h2>
        <p style={{
          fontSize: 18,
          color: "#444",
          maxWidth: 540,
          margin: "0 auto 32px",
        }}>
          Write everything you know — raw and unfiltered. Specview generates the documents your team needs to build it.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <a href="https://specview.dev/signup" style={{
            background: "#121212",
            color: "#FFFEF9",
            padding: "14px 32px",
            textDecoration: "none",
            fontFamily: "'Source Sans 3', sans-serif",
            fontSize: 14,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}>
            Try it free
          </a>
          <a href="#pricing" style={{
            border: "1px solid #121212",
            color: "#121212",
            padding: "14px 32px",
            textDecoration: "none",
            fontFamily: "'Source Sans 3', sans-serif",
            fontSize: 14,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            background: "transparent",
          }}>
            See pricing
          </a>
        </div>
      </section>

      {/* METRICS BAR */}
      <div style={{
        ...sectionStyle,
        display: "flex",
        justifyContent: "center",
        gap: 40,
        flexWrap: "wrap",
        padding: "24px",
        borderTop: "1px solid #ddd",
        borderBottom: "1px solid #ddd",
        marginBottom: 60,
      }}>
        {METRICS.map((m, i) => (
          <div key={i} style={{ textAlign: "center" }}>
            <div style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: 28,
              fontWeight: 700,
            }}>
              {m.value}
            </div>
            <div style={{
              fontSize: 12,
              color: "#888",
              fontFamily: "'Source Sans 3', sans-serif",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
            }}>
              {m.label}
            </div>
          </div>
        ))}
      </div>

      {/* WHAT GETS GENERATED */}
      <section id="what" style={{
        ...sectionStyle,
        padding: "0 24px 60px",
      }}>
        <div style={{
          borderTop: "3px solid #C0392B",
          paddingTop: 4,
          marginBottom: 32,
        }}>
          <h3 style={{
            fontFamily: "'Source Sans 3', sans-serif",
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#C0392B",
            margin: 0,
          }}>
            What gets generated
          </h3>
        </div>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 24,
        }}>
          {DOCS.map((d, i) => (
            <div key={i} style={{
              borderTop: "1px solid #121212",
              paddingTop: 16,
            }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>{d.icon}</div>
              <h4 style={{
                fontFamily: "'Playfair Display', Georgia, serif",
                fontSize: 20,
                fontWeight: 700,
                margin: "0 0 8px",
              }}>
                {d.name}
              </h4>
              <p style={{
                fontSize: 14,
                color: "#666",
                margin: 0,
                fontFamily: "'Source Sans 3', sans-serif",
              }}>
                {d.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" style={{
        ...sectionStyle,
        padding: "0 24px 60px",
      }}>
        <div style={{
          borderTop: "3px solid #C0392B",
          paddingTop: 4,
          marginBottom: 40,
        }}>
          <h3 style={{
            fontFamily: "'Source Sans 3', sans-serif",
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#C0392B",
            margin: 0,
          }}>
            How it works
          </h3>
        </div>
        {STEPS.map((s, i) => (
          <div key={i} style={{
            display: "grid",
            gridTemplateColumns: "48px 1fr",
            gap: 20,
            marginBottom: 48,
          }}>
            <div style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: 36,
              fontWeight: 700,
              color: "#C0392B",
              lineHeight: 1,
            }}>
              {s.num}
            </div>
            <div>
              <h4 style={{
                fontFamily: "'Playfair Display', Georgia, serif",
                fontSize: 24,
                fontWeight: 700,
                margin: "0 0 8px",
              }}>
                {s.title}
              </h4>
              <p style={{
                fontSize: 16,
                color: "#444",
                margin: "0 0 16px",
              }}>
                {s.desc}
              </p>
              <pre style={{
                background: "#141414",
                color: "#E8E6E0",
                padding: 20,
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
                lineHeight: 1.6,
                overflow: "auto",
                whiteSpace: "pre-wrap",
                border: "none",
              }}>
                {s.example}
              </pre>
            </div>
          </div>
        ))}
      </section>

      {/* COMPARISON */}
      <section style={{
        ...sectionStyle,
        padding: "0 24px 60px",
      }}>
        <div style={{
          borderTop: "3px solid #C0392B",
          paddingTop: 4,
          marginBottom: 32,
        }}>
          <h3 style={{
            fontFamily: "'Source Sans 3', sans-serif",
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#C0392B",
            margin: 0,
          }}>
            Specview vs AI app builders
          </h3>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 14,
            fontFamily: "'Source Sans 3', sans-serif",
          }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #121212" }}>
                <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 600 }}></th>
                <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 400, color: "#888" }}>Lovable / Bolt / Kiro</th>
                <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 700 }}>Specview</th>
              </tr>
            </thead>
            <tbody>
              {COMPARE.map((row, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "10px 12px", fontWeight: 600 }}>{row.dim}</td>
                  <td style={{ padding: "10px 12px", color: "#888" }}>{row.them}</td>
                  <td style={{ padding: "10px 12px" }}>{row.us}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* TESTIMONIAL */}
      <section style={{
        ...sectionStyle,
        padding: "40px 24px 60px",
        borderTop: "1px solid #ddd",
        borderBottom: "1px solid #ddd",
        marginBottom: 60,
      }}>
        <blockquote style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: 22,
          fontStyle: "italic",
          lineHeight: 1.5,
          textAlign: "center",
          maxWidth: 640,
          margin: "0 auto 16px",
          color: "#222",
        }}>
          "{TESTIMONIALS[0].quote}"
        </blockquote>
        <p style={{
          textAlign: "center",
          fontSize: 13,
          fontFamily: "'Source Sans 3', sans-serif",
          color: "#888",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}>
          — {TESTIMONIALS[0].author}
        </p>
      </section>

      {/* PRICING */}
      <section id="pricing" style={{
        ...sectionStyle,
        padding: "0 24px 60px",
      }}>
        <div style={{
          borderTop: "3px solid #C0392B",
          paddingTop: 4,
          marginBottom: 32,
        }}>
          <h3 style={{
            fontFamily: "'Source Sans 3', sans-serif",
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#C0392B",
            margin: 0,
          }}>
            Pricing
          </h3>
        </div>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 24,
        }}>
          {/* FREE */}
          <div style={{
            border: "1px solid #ddd",
            padding: 32,
          }}>
            <h4 style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: 24,
              margin: "0 0 4px",
            }}>
              Free
            </h4>
            <div style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: 36,
              fontWeight: 700,
              margin: "0 0 16px",
            }}>
              $0<span style={{ fontSize: 14, fontWeight: 400, color: "#888" }}> / month</span>
            </div>
            <ul style={{
              listStyle: "none",
              padding: 0,
              margin: "0 0 24px",
              fontFamily: "'Source Sans 3', sans-serif",
              fontSize: 14,
              color: "#444",
            }}>
              {["3 projects / month", "Full spec generation pipeline", "Analysis, epic, architecture, timeline", "No credit card required"].map((item, i) => (
                <li key={i} style={{ padding: "6px 0", borderBottom: "1px solid #f0f0f0" }}>
                  {item}
                </li>
              ))}
            </ul>
            <a href="https://specview.dev/signup" style={{
              display: "block",
              textAlign: "center",
              border: "1px solid #121212",
              color: "#121212",
              padding: "12px",
              textDecoration: "none",
              fontFamily: "'Source Sans 3', sans-serif",
              fontSize: 13,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}>
              Try it free
            </a>
          </div>

          {/* PRO */}
          <div style={{
            border: "2px solid #121212",
            padding: 32,
          }}>
            <h4 style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: 24,
              margin: "0 0 4px",
            }}>
              Pro
            </h4>
            <div style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: 36,
              fontWeight: 700,
              margin: "0 0 16px",
            }}>
              $29<span style={{ fontSize: 14, fontWeight: 400, color: "#888" }}> / month</span>
            </div>
            <ul style={{
              listStyle: "none",
              padding: 0,
              margin: "0 0 24px",
              fontFamily: "'Source Sans 3', sans-serif",
              fontSize: 14,
              color: "#444",
            }}>
              {["Unlimited projects", "Full spec generation pipeline", "Analysis, epic, architecture, timeline", "Implementation guides with test bodies", "Priority support"].map((item, i) => (
                <li key={i} style={{ padding: "6px 0", borderBottom: "1px solid #f0f0f0" }}>
                  {item}
                </li>
              ))}
            </ul>
            <a href="https://buy.stripe.com/test_xxx" style={{
              display: "block",
              textAlign: "center",
              background: "#121212",
              color: "#FFFEF9",
              padding: "12px",
              textDecoration: "none",
              fontFamily: "'Source Sans 3', sans-serif",
              fontSize: 13,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}>
              Get Pro — $29/mo
            </a>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section style={{
        ...sectionStyle,
        padding: "0 24px 60px",
      }}>
        <div style={{
          borderTop: "3px solid #C0392B",
          paddingTop: 4,
          marginBottom: 32,
        }}>
          <h3 style={{
            fontFamily: "'Source Sans 3', sans-serif",
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#C0392B",
            margin: 0,
          }}>
            Questions
          </h3>
        </div>
        {FAQ.map((f, i) => (
          <div key={i} style={{
            borderBottom: "1px solid #eee",
            cursor: "pointer",
          }} onClick={() => setOpenFaq(openFaq === i ? null : i)}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "16px 0",
            }}>
              <span style={{
                fontFamily: "'Playfair Display', Georgia, serif",
                fontSize: 18,
                fontWeight: 600,
              }}>
                {f.q}
              </span>
              <span style={{
                fontSize: 20,
                color: "#888",
                transform: openFaq === i ? "rotate(45deg)" : "none",
                transition: "transform 0.2s",
              }}>
                +
              </span>
            </div>
            {openFaq === i && (
              <p style={{
                fontSize: 15,
                color: "#444",
                margin: "0 0 16px",
                paddingLeft: 0,
                fontFamily: "'Source Sans 3', sans-serif",
                lineHeight: 1.7,
              }}>
                {f.a}
              </p>
            )}
          </div>
        ))}
      </section>

      {/* FOOTER */}
      <footer style={{
        ...sectionStyle,
        borderTop: "3px solid #121212",
        padding: "24px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 40,
        flexWrap: "wrap",
        gap: 16,
      }}>
        <span style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: 14,
        }}>
          Specview · Built by Sam · Powered by Claude
        </span>
        <div style={{
          display: "flex",
          gap: 20,
          fontSize: 13,
          fontFamily: "'Source Sans 3', sans-serif",
        }}>
          <a href="https://github.com/bytesbysamu/specview" style={{ color: "#888", textDecoration: "none" }}>GitHub</a>
          <a href="https://x.com/bytesbysamu" style={{ color: "#888", textDecoration: "none" }}>Twitter/X</a>
          <a href="mailto:sam@specview.io" style={{ color: "#888", textDecoration: "none" }}>Contact</a>
        </div>
      </footer>
    </div>
  );
}
