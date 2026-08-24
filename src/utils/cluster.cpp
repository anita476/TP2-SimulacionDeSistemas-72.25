#include "cluster.hpp"

#include <algorithm>
#include <unordered_map>
#include <unordered_set>

Clusters find_clusters(const NeighborLists &neighbors) {
	std::unordered_map<int, int> node_cluster;
	std::unordered_map<int, std::unordered_set<int>> cluster_nodes;
	int next_cluster = 0;

	for (int node = 0; node < static_cast<int>(neighbors.size()); ++node) {
		std::unordered_set<int> touched_clusters;
		auto node_it = node_cluster.find(node);
		if (node_it != node_cluster.end())
			touched_clusters.insert(node_it->second);

		for (int neighbor : neighbors[static_cast<std::size_t>(node)]) {
			auto neighbor_it = node_cluster.find(neighbor);
			if (neighbor_it != node_cluster.end())
				touched_clusters.insert(neighbor_it->second);
		}

		const int target_cluster = touched_clusters.empty()
																	 ? next_cluster++
																	 : *touched_clusters.begin();
		auto &target_nodes = cluster_nodes[target_cluster];
		target_nodes.insert(node);
		node_cluster[node] = target_cluster;

		for (int neighbor : neighbors[static_cast<std::size_t>(node)]) {
			target_nodes.insert(neighbor);
			node_cluster[neighbor] = target_cluster;
		}

		for (int old_cluster : touched_clusters) {
			if (old_cluster == target_cluster)
				continue;
			auto old_nodes_it = cluster_nodes.find(old_cluster);
			if (old_nodes_it == cluster_nodes.end())
				continue;
			for (int member : old_nodes_it->second) {
				target_nodes.insert(member);
				node_cluster[member] = target_cluster;
			}
			cluster_nodes.erase(old_nodes_it);
		}
	}

	Clusters result;
	result.reserve(cluster_nodes.size());
	for (auto &[cluster_id, members] : cluster_nodes) {
		(void)cluster_id;
		Cluster cluster(members.begin(), members.end());
		std::sort(cluster.begin(), cluster.end());
		result.push_back(std::move(cluster));
	}
	std::sort(result.begin(), result.end(), [](const Cluster &left, const Cluster &right) {
		return left.front() < right.front();
	});
	return result;
}

double cluster_observable_s(const Clusters &clusters) {
	std::size_t total_nodes = 0;
	std::size_t largest_cluster = 0;
	for (const Cluster &cluster : clusters) {
		total_nodes += cluster.size();
		largest_cluster = std::max(largest_cluster, cluster.size());
	}
	return total_nodes == 0
						 ? 0.0
						 : static_cast<double>(largest_cluster) / total_nodes;
}
