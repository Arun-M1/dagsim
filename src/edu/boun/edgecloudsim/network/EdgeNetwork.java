package edu.boun.edgecloudsim.network;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.Map;
import java.util.Queue;
import java.util.Set;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

/**
 * Stores links between edge datacenter locations.
 * Each location ID is the location's configured wlan_id value.
 * Mobile devices themselves are not graph nodes.
 */
public class EdgeNetwork {
    private final Map<Integer, Set<Integer>> neighbors = new LinkedHashMap<Integer, Set<Integer>>();

    public EdgeNetwork(Document edgeDevicesDocument) {
        if (edgeDevicesDocument == null) {
            throw new IllegalArgumentException("Edge devices document cannot be null");
        }

        readDCNodes(edgeDevicesDocument);
        readDCLinks(edgeDevicesDocument);
        if (!isConnected()) {
            throw new IllegalArgumentException("Edge network is disconnected");
        }
    }

    /**
     * @param curLocationId mobile device's current location, identified by its wlan_id
     * @param targetDcLocationId selected edge datacenter location, identified by its wlan_id
     */
    public int getLeastHops(int curLocationId, int targetDcLocationId) {
        if (!locationIdExists(curLocationId)) {
            throw new IllegalArgumentException("Unknown current location ID: " + curLocationId);
        }
        if (!locationIdExists(targetDcLocationId)) {
            throw new IllegalArgumentException("Unknown target edge datacenter location ID: "
                    + targetDcLocationId);
        }

        if (curLocationId == targetDcLocationId) {
            return 0;
        }

        Queue<Integer> toVisit = new LinkedList<Integer>();
        Map<Integer, Integer> hops = new LinkedHashMap<Integer, Integer>();
        toVisit.add(curLocationId);
        hops.put(curLocationId, 0);
        
        //bfs
        while (!toVisit.isEmpty()) {
            int currentId = toVisit.remove();
            int nextHopCount = hops.get(currentId) + 1;

            for (int neighborId : neighbors.get(currentId)) {
                if (hops.containsKey(neighborId)) {
                    continue;
                }
                if (neighborId == targetDcLocationId) {
                    return nextHopCount;
                }

                hops.put(neighborId, nextHopCount);
                toVisit.add(neighborId);
            }
        }

        throw new IllegalStateException("No edge route from current location " + curLocationId
                + " to target edge datacenter location " + targetDcLocationId);
    }

    private void readDCNodes(Document edgeDevicesDocument) {
        NodeList dcNodes = edgeDevicesDocument.getElementsByTagName("datacenter");
        for (int i = 0; i < dcNodes.getLength(); i++) {
            Element dc = (Element) dcNodes.item(i);
            Element location = (Element) dc.getElementsByTagName("location").item(0);
            int locationId = Integer.parseInt(location.getElementsByTagName("wlan_id").item(0)
                    .getTextContent().trim());

            if (neighbors.put(locationId, new LinkedHashSet<Integer>()) != null) {
                throw new IllegalArgumentException("Duplicate edge datacenter location ID: " + locationId);
            }
        }

        if (neighbors.isEmpty()) {
            throw new IllegalArgumentException("No edge datacenters were found in the edge devices document");
        }
    }

    private void readDCLinks(Document edgeDevicesDocument) {
        NodeList links = edgeDevicesDocument.getElementsByTagName("link");
        for (int i = 0; i < links.getLength(); i++) {
            Element link = (Element) links.item(i);
            int fromId = readWlanId(link, "from_wlan_id");
            int toId = readWlanId(link, "to_wlan_id");

            if (!locationIdExists(fromId)) {
                throw new IllegalArgumentException("Unknown edge datacenter location ID: " + fromId);
            }
            if (!locationIdExists(toId)) {
                throw new IllegalArgumentException("Unknown edge datacenter location ID: " + toId);
            }
            if (fromId == toId) {
                throw new IllegalArgumentException("An edge link cannot connect location "
                        + fromId + " to itself");
            }

            neighbors.get(fromId).add(toId);
            neighbors.get(toId).add(fromId);
        }
    }

    private int readWlanId(Element link, String attributeName) {
        String value = link.getAttribute(attributeName);
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("Edge link is missing attribute " + attributeName);
        }
        return Integer.parseInt(value.trim());
    }

    private boolean locationIdExists(int locationId) {
        return neighbors.containsKey(locationId);
    }

    private boolean isConnected() {
        int startId = neighbors.keySet().iterator().next();
        Set<Integer> visited = new LinkedHashSet<Integer>();
        Queue<Integer> toVisit = new LinkedList<Integer>();
        toVisit.add(startId);

        while (!toVisit.isEmpty()) {
            int currentId = toVisit.remove();
            if (!visited.add(currentId)) {
                continue;
            }
            toVisit.addAll(neighbors.get(currentId));
        }

        return visited.size() == neighbors.size();
    }
}
