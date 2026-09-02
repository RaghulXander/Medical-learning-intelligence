/**
 * apps/mobile/components/ErrorBoundary.tsx
 *
 * Milestone 17.1: Application-Wide React Error Boundary with Automatic
 * Privacy-Sanitized Release Diagnostics Reporting.
 */

import React, { Component, ReactNode } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Platform } from 'react-native';
import { AlertTriangle, RefreshCw } from 'lucide-react-native';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { diagnosticsApi } from '@medical/api-client';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string;
  reportId?: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      errorMessage: '',
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error?.message || 'An unexpected runtime error occurred.',
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('[DocEdge ErrorBoundary Catch]:', error, errorInfo);

    // Asynchronously dispatch privacy-sanitized crash telemetry
    diagnosticsApi
      .submitCrashReport({
        app_version: '1.0.1',
        runtime_version: '1.0.1',
        git_tag: 'android-beta-v1.0.1',
        os_name: Platform.OS,
        os_version: String(Platform.Version),
        category: 'REACT_RENDER_FATAL',
        error_message: error?.message || 'Unknown render error',
        stack_trace: `${error?.stack || ''}\nComponentStack: ${errorInfo.componentStack || ''}`,
      })
      .then((res) => {
        if (res?.report_id) {
          this.setState({ reportId: res.report_id });
        }
      })
      .catch(() => {
        // Silently swallow reporting failure to avoid cascading crashes
      });
  }

  handleReset = () => {
    this.setState({ hasError: false, errorMessage: '', reportId: undefined });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.container}>
            <View style={styles.iconBox}>
              <AlertTriangle size={36} color="#ef4444" />
            </View>

            <Text style={styles.title}>Something went wrong</Text>
            <Text style={styles.subtitle}>
              DocEdge encountered an unexpected error. Your assessment answers and streak progress are auto-saved.
            </Text>

            <Card style={styles.errorCard}>
              <Text style={styles.errorLabel}>Diagnostic Summary</Text>
              <Text style={styles.errorText} numberOfLines={4}>
                {this.state.errorMessage}
              </Text>
              {this.state.reportId ? (
                <Text style={styles.reportIdText}>Reference ID: {this.state.reportId}</Text>
              ) : null}
            </Card>

            <Button
              title="Reload Screen"
              variant="primary"
              size="lg"
              onPress={this.handleReset}
              icon={<RefreshCw size={18} color="#ffffff" />}
              style={{ marginTop: 24, width: '100%' }}
            />
          </View>
        </SafeAreaView>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#020617',
  },
  container: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconBox: {
    width: 68,
    height: 68,
    borderRadius: 22,
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 22,
    color: '#94a3b8',
    textAlign: 'center',
    marginBottom: 24,
    paddingHorizontal: 8,
  },
  errorCard: {
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
    width: '100%',
    padding: 16,
  },
  errorLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  errorText: {
    fontSize: 13,
    lineHeight: 18,
    color: '#f87171',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  reportIdText: {
    fontSize: 11,
    color: '#38bdf8',
    marginTop: 8,
  },
});
