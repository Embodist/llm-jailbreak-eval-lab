"use client";

import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#7c5cff" },
    secondary: { main: "#22d3ee" },
    background: { default: "#0a0e17", paper: "#121a27" },
    text: { primary: "#e6edf7", secondary: "#8b9bb4" },
    divider: "rgba(255,255,255,0.08)",
    success: { main: "#22c55e" },
    warning: { main: "#f59e0b" },
    error: { main: "#ef4444" },
  },
  shape: { borderRadius: 14 },
  typography: {
    fontFamily:
      'Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
    h4: { fontWeight: 700, letterSpacing: "-0.02em" },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 650 },
    subtitle2: { color: "#8b9bb4" },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage:
            "linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0))",
          border: "1px solid rgba(255,255,255,0.07)",
        },
      },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
  },
});

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}
