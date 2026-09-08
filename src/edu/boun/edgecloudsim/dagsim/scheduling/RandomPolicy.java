package edu.boun.edgecloudsim.dagsim.scheduling;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Random scheduling baseline.
 *
 * The policy samples uniformly from the valid tier + datacenter actions used
 * by the RL policy. It intentionally does not choose a VM. DagAwareOrchestrator
 * performs the existing VM selection after this policy chooses the destination
 * tier and datacenter.
 */
public class RandomPolicy implements SchedulingPolicy {
    private final Random random;

    public RandomPolicy() {
        this.random = new Random();
    }

    public RandomPolicy(long seed) {
        this.random = new Random(seed);
    }

    @Override
    public PlacementDecision decide(TaskContext task, ClusterState state) {
        List<Candidate> candidates = new ArrayList<>();

        if (state != null && state.vms != null) {
            // Preserve the RL action ordering: all edge datacenters first,
            // followed by all cloud datacenters.
            addDatacenterCandidates(candidates, state, PlacementDecision.TIER_EDGE);
            addDatacenterCandidates(candidates, state, PlacementDecision.TIER_CLOUD);
        }

        if (candidates.isEmpty()) {
            // Match the existing policies' safe default when cluster state is
            // unavailable. The orchestrator will return null if no VM exists.
            return new PlacementDecision(PlacementDecision.TIER_EDGE, 0, 0);
        }

        Candidate selected = candidates.get(random.nextInt(candidates.size()));

        // destVmId is only a placeholder. DagAwareOrchestrator deliberately
        // ignores it and selects a VM inside the chosen datacenter.
        return new PlacementDecision(selected.tier, selected.datacenterId, 0);
    }

    private void addDatacenterCandidates(List<Candidate> candidates, ClusterState state, int tier) {
        if (tier < 0 || tier >= state.vms.length || state.vms[tier] == null) {
            return;
        }

        for (int dc = 0; dc < state.vms[tier].length; dc++) {
            ClusterState.VMInfo[] dcVms = state.vms[tier][dc];
            if (hasAvailableVmEntry(dcVms)) {
                candidates.add(new Candidate(tier, dc));
            }
        }
    }

    private boolean hasAvailableVmEntry(ClusterState.VMInfo[] dcVms) {
        if (dcVms == null || dcVms.length == 0) {
            return false;
        }

        for (ClusterState.VMInfo vm : dcVms) {
            if (vm != null) {
                return true;
            }
        }
        return false;
    }

    @Override
    public String getPolicyName() {
        return "Random";
    }

    private static class Candidate {
        private final int tier;
        private final int datacenterId;

        private Candidate(int tier, int datacenterId) {
            this.tier = tier;
            this.datacenterId = datacenterId;
        }
    }
}
