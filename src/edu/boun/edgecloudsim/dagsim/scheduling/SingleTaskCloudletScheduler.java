package edu.boun.edgecloudsim.dagsim.scheduling;

import org.cloudbus.cloudsim.Cloudlet;
import org.cloudbus.cloudsim.CloudletSchedulerSpaceShared;
import org.cloudbus.cloudsim.ResCloudlet;
import org.cloudbus.cloudsim.core.CloudSim;

import edu.boun.edgecloudsim.edge_client.Task;

/**
 * A FIFO cloudlet scheduler that allows at most one task to execute on a VM.
 * Additional tasks remain in CloudSim's waiting list until the running task
 * finishes.
 */
public class SingleTaskCloudletScheduler extends CloudletSchedulerSpaceShared {

    @Override
    public double cloudletSubmit(Cloudlet cloudlet, double fileTransferTime) {
        if (cloudlet instanceof Task) {
            ((Task) cloudlet).setVmQueueArrivalTimeMs(CloudSim.clock() * 1000.0);
        }

        if (!getCloudletExecList().isEmpty() || !getCloudletWaitingList().isEmpty()) {
            ResCloudlet waitingCloudlet = new ResCloudlet(cloudlet);
            waitingCloudlet.setCloudletStatus(Cloudlet.QUEUED);
            getCloudletWaitingList().add(waitingCloudlet);
            return 0.0;
        }

        double completionDelay = super.cloudletSubmit(cloudlet, fileTransferTime);
        if (completionDelay > 0.0 && !Double.isInfinite(completionDelay)) {
            return Math.max(completionDelay, CloudSim.getMinTimeBetweenEvents());
        }
        return completionDelay;
    }
}
