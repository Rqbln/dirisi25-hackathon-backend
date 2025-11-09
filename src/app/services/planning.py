"""Service de planification et allocation de ressources."""

from typing import Any

from app.logging_conf import get_logger
from app.schemas.planning import (
    ActionType,
    EstimatedGain,
    Objective,
    PlanAction,
    PlanRequest,
    PlanResponse,
)

logger = get_logger(__name__)


class PlanningService:
    """Service de planification basé sur des heuristiques greedy."""

    def __init__(self):
        """Initialise le service de planification."""
        pass

    def generate_plan(
        self,
        request: PlanRequest,
        topology: dict,
        risk_scores: dict[str, float],
    ) -> PlanResponse:
        """Génère un plan d'action.

        Args:
            request: Requête de planification
            topology: Topologie du réseau
            risk_scores: Scores de risque par entité

        Returns:
            Plan d'action recommandé
        """
        logger.info(
            f"Generating plan with objectives: {request.objectives}"
        )

        actions = []
        rationale = []

        # Identifier les éléments à haut risque
        high_risk_entities = [
            entity_id
            for entity_id, score in risk_scores.items()
            if score > 0.6
        ]

        # Traiter chaque objectif
        if Objective.MINIMIZE_RISK in request.objectives:
            risk_actions = self._handle_minimize_risk(
                high_risk_entities,
                request,
                topology,
            )
            actions.extend(risk_actions["actions"])
            rationale.extend(risk_actions["rationale"])

        if Objective.PRESERVE_CRITICAL_FLOWS in request.objectives:
            flow_actions = self._handle_preserve_critical_flows(
                request,
                topology,
                high_risk_entities,
            )
            actions.extend(flow_actions["actions"])
            rationale.extend(flow_actions["rationale"])

        if Objective.BALANCE_LOAD in request.objectives:
            balance_actions = self._handle_balance_load(
                topology,
                risk_scores,
            )
            actions.extend(balance_actions["actions"])
            rationale.extend(balance_actions["rationale"])

        # Calculer les gains estimés
        estimated_gain = self._estimate_gain(
            actions,
            high_risk_entities,
            risk_scores,
        )

        return PlanResponse(
            actions=actions,
            rationale=rationale,
            estimated_gain=estimated_gain,
        )

    def _handle_minimize_risk(
        self,
        high_risk_entities: list[str],
        request: PlanRequest,
        topology: dict,
    ) -> dict[str, list]:
        """Gère l'objectif de minimisation du risque.

        Args:
            high_risk_entities: Entités à haut risque
            request: Requête
            topology: Topologie

        Returns:
            Dict avec actions et rationale
        """
        actions = []
        rationale = []

        for entity_id in high_risk_entities:
            if entity_id.startswith("N"):
                # Nœud à haut risque -> isoler si critique
                if entity_id in request.context.impacted:
                    actions.append(
                        PlanAction(
                            type=ActionType.ISOLATE,
                            node=entity_id,
                        )
                    )
                    rationale.append(f"Isolate high-risk node {entity_id}")

            elif entity_id.startswith("L"):
                # Lien à haut risque -> reroutage si possible
                link = self._find_link(entity_id, topology)
                if link:
                    # Trouver un chemin alternatif (simplifié)
                    alt_path = self._find_alternative_path(link, topology)
                    if alt_path:
                        actions.append(
                            PlanAction(
                                type=ActionType.REROUTE,
                                flow=f"FLOW_{entity_id}",
                                via=alt_path,
                            )
                        )
                        rationale.append(
                            f"Reroute traffic from congested link {entity_id}"
                        )

        return {"actions": actions, "rationale": rationale}

    def _handle_preserve_critical_flows(
        self,
        request: PlanRequest,
        topology: dict,
        high_risk_entities: list[str],
    ) -> dict[str, list]:
        """Gère la préservation des flows critiques.

        Args:
            request: Requête
            topology: Topologie
            high_risk_entities: Entités à haut risque

        Returns:
            Dict avec actions et rationale
        """
        actions = []
        rationale = []

        for flow_id in request.context.critical_flows:
            # Vérifier si le flow traverse une zone à risque
            for entity_id in high_risk_entities:
                if entity_id.startswith("L"):
                    # Proposer un reroutage
                    link = self._find_link(entity_id, topology)
                    if link:
                        alt_path = self._find_alternative_path(link, topology)
                        if alt_path:
                            actions.append(
                                PlanAction(
                                    type=ActionType.REROUTE,
                                    flow=flow_id,
                                    via=alt_path,
                                )
                            )
                            rationale.append(
                                f"Protect critical flow {flow_id} by rerouting"
                            )
                            break

        return {"actions": actions, "rationale": rationale}

    def _handle_balance_load(
        self,
        topology: dict,
        risk_scores: dict[str, float],
    ) -> dict[str, list]:
        """Gère l'équilibrage de charge.

        Args:
            topology: Topologie
            risk_scores: Scores de risque

        Returns:
            Dict avec actions et rationale
        """
        actions = []
        rationale = []

        # Identifier les nœuds sous-utilisés
        nodes = topology.get("nodes", [])
        for node in nodes:
            node_id = node["id"]
            score = risk_scores.get(node_id, 0)

            if score < 0.3:  # Nœud peu chargé
                # Proposer de décaler de la charge
                actions.append(
                    PlanAction(
                        type=ActionType.SHIFT_RESERVE,
                        node=node_id,
                        delta_mbps=100,
                    )
                )
                rationale.append(
                    f"Increase reserve capacity on underutilized node {node_id}"
                )

        return {"actions": actions, "rationale": rationale}

    def _find_link(self, link_id: str, topology: dict) -> dict | None:
        """Trouve un lien par son ID.

        Args:
            link_id: ID du lien
            topology: Topologie

        Returns:
            Dictionnaire du lien ou None
        """
        links = topology.get("links", [])
        for link in links:
            if link["id"] == link_id:
                return link
        return None

    def _find_alternative_path(
        self, link: dict, topology: dict
    ) -> list[str] | None:
        """Trouve un chemin alternatif (heuristique simple).

        Args:
            link: Lien à contourner
            topology: Topologie

        Returns:
            Liste d'IDs de liens alternatifs ou None
        """
        # Algorithme simplifié : trouver un autre lien entre src et dst
        src = link["src"]
        dst = link["dst"]
        links = topology.get("links", [])

        # Chercher un chemin indirect
        for intermediate_link in links:
            if (
                intermediate_link["id"] != link["id"]
                and intermediate_link["src"] == src
            ):
                # Trouver un second lien
                intermediate_node = intermediate_link["dst"]
                for second_link in links:
                    if (
                        second_link["src"] == intermediate_node
                        and second_link["dst"] == dst
                    ):
                        return [intermediate_link["id"], second_link["id"]]

        return None

    def _estimate_gain(
        self,
        actions: list[PlanAction],
        high_risk_entities: list[str],
        risk_scores: dict[str, float],
    ) -> EstimatedGain:
        """Estime le gain du plan.

        Args:
            actions: Actions proposées
            high_risk_entities: Entités à haut risque
            risk_scores: Scores de risque

        Returns:
            Gains estimés
        """
        # Estimation simplifiée
        num_reroutes = sum(
            1 for a in actions if a.type == ActionType.REROUTE
        )
        num_isolations = sum(
            1 for a in actions if a.type == ActionType.ISOLATE
        )

        # Réduction du risque proportionnelle aux actions
        risk_delta = -0.15 * num_reroutes - 0.10 * num_isolations

        # Violations SLA évitées
        sla_violations_avoided = len(high_risk_entities) // 2

        return EstimatedGain(
            risk_delta=risk_delta,
            sla_violations_avoided=sla_violations_avoided,
        )
