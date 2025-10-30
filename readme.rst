::

  ┏━━━━━━━━━━━━━━━━━━┓
  ┃ original sources ┠─┐
  ┗━┯━━━━━━━━━━━━━━━━┛ │
    └──────────────────┘         ╔═════════════════════╗
       ┏━━━━━━━━━━━━━┓           ║                     ║         ┏━━━━━━━━━━━━━━━┓
       ┃ new sources ┠─┐         ║    \           /    ║         ┃ clean patches ┠─┐
       ┗━┯━━━━━━━━━━━┛ │  ━━━━🭬  ║   ── PATCHTREE ──   ║  ━━━━🭬  ┗━┯━━━━━━━━━━━━━┛ ├─┐
         └─────────────┘         ║    /           \    ║           └─┬─────────────┘ │
  ┏━━━━━━━━━━━━━━━━━━┓           ║                     ║             └───────────────┘
  ┃ semantic patches ┠─┐         ╚═════════════════════╝
  ┗━┯━━━━━━━━━━━━━━━━┛ │
    └──────────────────┘

Patchtree is a tool for generating clean patches for external source trees.
It allows both patch sources to be maintained separately from the sources they apply to, and templating or scripting of the patches themselves in order to adjust to variations in the external source tree.
This makes it a useful for automating the process of backporting bugfixes or adding functionality to existing software releases.
