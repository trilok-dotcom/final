import React, { useEffect, useState, useCallback } from 'react';
import type { EvaluationOverview, EvaluationRun } from '../types/evaluation';
import { evaluationService } from '../services/evaluation';

import { EvaluationSummary } from '../components/evaluation/EvaluationSummary';
import { AIMetricsPanel } from '../components/evaluation/AIMetricsPanel';
import { ThresholdAnalysisPanel } from '../components/evaluation/ThresholdAnalysisPanel';
import { InferencePerformancePanel } from '../components/evaluation/InferencePerformancePanel';
import { RoutingMetricsPanel } from '../components/evaluation/RoutingMetricsPanel';
import { ResourceMetricsPanel } from '../components/evaluation/ResourceMetricsPanel';
import { MissionMetricsPanel } from '../components/evaluation/MissionMetricsPanel';
import { ReroutingMetricsPanel } from '../components/evaluation/ReroutingMetricsPanel';
import { SimulationMetricsPanel } from '../components/evaluation/SimulationMetricsPanel';
import { BaselineComparisonPanel } from '../components/evaluation/BaselineComparisonPanel';
import { EvaluationHistory } from '../components/evaluation/EvaluationHistory';

export const EvaluationCenter: React.FC = () => {
  const [overview, setOverview] = useState<EvaluationOverview | null>(null);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [thresholdCurve, setThresholdCurve] = useState<any[]>([]);
  const [latencyStats, setLatencyStats] = useState<any | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [ovData, runsData] = await Promise.all([
        evaluationService.getOverview(),
        evaluationService.getRuns(),
      ]);
      setOverview(ovData);
      setRuns(runsData);

      // If AI model run exists, load detailed run info for threshold curve & latency stats
      const aiRun = runsData.find((r) => r.evaluation_type === 'AI_MODEL' && r.status === 'COMPLETED');
      if (aiRun) {
        const fullRun = await evaluationService.getRun(aiRun.id);
        if (fullRun.metadata?.threshold_curve) {
          setThresholdCurve(fullRun.metadata.threshold_curve);
        }
        if (fullRun.metadata?.latency_stats) {
          setLatencyStats(fullRun.metadata.latency_stats);
        }
      }
    } catch (err) {
      console.error('Error loading evaluation data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunAiEval = async () => {
    setLoading(true);
    try {
      await evaluationService.runAiEval(20);
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to run AI evaluation');
    } finally {
      setLoading(false);
    }
  };

  const handleRunRoutingEval = async () => {
    setLoading(true);
    try {
      await evaluationService.runRoutingEval(20);
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to run routing evaluation');
    } finally {
      setLoading(false);
    }
  };

  const handleRunReroutingEval = async () => {
    setLoading(true);
    try {
      await evaluationService.runReroutingEval();
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to run rerouting evaluation');
    } finally {
      setLoading(false);
    }
  };

  const handleRunResourcesEval = async () => {
    setLoading(true);
    try {
      await evaluationService.runResourcesEval();
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to run resources evaluation');
    } finally {
      setLoading(false);
    }
  };

  const handleRunMissionsEval = async () => {
    setLoading(true);
    try {
      await evaluationService.runMissionsEval();
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to run missions evaluation');
    } finally {
      setLoading(false);
    }
  };

  const handleRunOsrmBaseline = async () => {
    setLoading(true);
    try {
      await evaluationService.runOsrmBaseline();
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to run OSRM baseline evaluation');
    } finally {
      setLoading(false);
    }
  };

  const handleRunNearestUnitBaseline = async () => {
    setLoading(true);
    try {
      await evaluationService.runNearestUnitBaseline();
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to run Nearest Unit baseline evaluation');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAll = async () => {
    setLoading(true);
    try {
      await evaluationService.runAiEval(10);
      await evaluationService.runRoutingEval(10);
      await evaluationService.runReroutingEval();
      await evaluationService.runResourcesEval();
      await evaluationService.runMissionsEval();
      await evaluationService.runOsrmBaseline();
      await evaluationService.runNearestUnitBaseline();
      await loadData();
    } catch (err) {
      console.error(err);
      alert('Error running full evaluation chain');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <EvaluationSummary
        overview={overview}
        loading={loading}
        onRunAll={handleRunAll}
        onRefresh={loadData}
      />

      <AIMetricsPanel
        overview={overview}
        onRunAiEval={handleRunAiEval}
        loading={loading}
      />

      <ThresholdAnalysisPanel
        thresholdCurve={thresholdCurve}
        bestThreshold={overview?.ai?.best_threshold ?? null}
        bestDice={overview?.ai?.best_dice ?? null}
        productionThreshold={overview?.system_info?.production_threshold ?? 0.25}
      />

      <InferencePerformancePanel latencyStats={latencyStats} />

      <RoutingMetricsPanel
        overview={overview}
        onRunRoutingEval={handleRunRoutingEval}
        loading={loading}
      />

      <ResourceMetricsPanel
        overview={overview}
        onRunResourcesEval={handleRunResourcesEval}
        loading={loading}
      />

      <MissionMetricsPanel
        overview={overview}
        onRunMissionsEval={handleRunMissionsEval}
        loading={loading}
      />

      <ReroutingMetricsPanel
        overview={overview}
        onRunReroutingEval={handleRunReroutingEval}
        loading={loading}
      />

      <SimulationMetricsPanel overview={overview} />

      <BaselineComparisonPanel
        overview={overview}
        onRunOsrmBaseline={handleRunOsrmBaseline}
        onRunNearestUnitBaseline={handleRunNearestUnitBaseline}
        loading={loading}
      />

      <EvaluationHistory runs={runs} onRefresh={loadData} />
    </div>
  );
};
