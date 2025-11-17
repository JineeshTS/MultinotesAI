import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        port: "5173",
    },
    build: {
        minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Removes all console statements (log, warn, error, info)
      },
    },
    }
});

// stripe public key
// pk_test_51OjJKWSJago1WNDSjLcH75nK60n7G2ROwL8blkGvTYrnDkRbvgnJoiQa5hpfLf0HsJYqA4c3oFRLZz7OtXDfTWX600KxFYTcxO