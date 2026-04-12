/**
 * Dashboard barrel -- re-exports Arrow IPC helpers and timeline utilities.
 *
 * Dashboard plugins alias "shenas-frontends" to this file for dev/test
 * resolution. In production the full vendor bundle is used instead.
 */

export * from "./arrow.ts";
export * from "./timeline-utils.ts";
