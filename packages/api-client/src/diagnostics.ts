/**
 * packages/api-client/src/diagnostics.ts
 *
 * Milestone 17.1: Client Error and Crash Reporting Client.
 */

import { ApiClient } from './client';

export interface CrashReportPayload {
  app_version: string;
  runtime_version?: string;
  git_tag?: string;
  os_name?: string;
  os_version?: string;
  device_model?: string;
  category?: string;
  error_message: string;
  stack_trace?: string;
  request_id?: string;
  metadata?: Record<string, any>;
}

export interface CrashReportResponse {
  success: boolean;
  report_id: string;
  received_at: string;
  status: string;
}

export class DiagnosticsApi {
  private client: ApiClient;

  constructor(client: ApiClient = new ApiClient()) {
    this.client = client;
  }

  public async submitCrashReport(payload: CrashReportPayload): Promise<CrashReportResponse> {
    return this.client.request<CrashReportResponse>('/api/diagnostics/crash-report', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const diagnosticsApi = new DiagnosticsApi();
