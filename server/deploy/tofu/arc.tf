# Actions Runner Controller (ARC) for self-hosted GitHub Actions runners on GKE

resource "kubernetes_namespace" "arc_systems" {
  metadata {
    name = "arc-systems"
  }
}

resource "kubernetes_namespace" "arc_runners" {
  metadata {
    name = "arc-runners"
  }
}

resource "kubernetes_secret" "arc_github_app" {
  metadata {
    name      = "github-app-secret"
    namespace = kubernetes_namespace.arc_runners.metadata[0].name
  }

  data = {
    github_app_id              = var.arc_app_id
    github_app_installation_id = var.arc_app_installation_id
    github_app_private_key     = var.arc_app_private_key
  }
}

# ARC controller
resource "helm_release" "arc_controller" {
  name             = "arc"
  namespace        = kubernetes_namespace.arc_systems.metadata[0].name
  repository       = "oci://ghcr.io/actions/actions-runner-controller-charts"
  chart            = "gha-runner-scale-set-controller"
  version          = "0.12.1"
  create_namespace = false

  set {
    name  = "fullnameOverride"
    value = "arc-gha-rs-controller"
  }

  values = [
    <<-EOT
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
        ephemeral-storage: 1Gi
      limits:
        cpu: 100m
        memory: 128Mi
        ephemeral-storage: 1Gi
    EOT
  ]
}

# Runner scale set
resource "helm_release" "arc_runner_set" {
  name             = "arc-runner-set"
  namespace        = kubernetes_namespace.arc_runners.metadata[0].name
  repository       = "oci://ghcr.io/actions/actions-runner-controller-charts"
  chart            = "gha-runner-scale-set"
  version          = "0.12.1"
  create_namespace = false

  values = [
    <<-EOT
    githubConfigUrl: https://github.com/${var.github_repo}
    githubConfigSecret: ${kubernetes_secret.arc_github_app.metadata[0].name}
    runnerScaleSetName: gcp-runners
    minRunners: 0
    maxRunners: 5
    controllerServiceAccount:
      name: arc-gha-rs-controller
      namespace: arc-systems
    template:
      spec:
        securityContext:
          runAsUser: 1001
          runAsGroup: 1001
          fsGroup: 1001
          runAsNonRoot: true
          seccompProfile:
            type: RuntimeDefault
        volumes:
        - name: work
          emptyDir: {}
        containers:
        - name: runner
          image: ${var.region}-docker.pkg.dev/${var.project}/shenas/ci-runner:latest
          command: ["/home/runner/run.sh"]
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          volumeMounts:
          - name: work
            mountPath: /home/runner/_work
          resources:
            requests:
              cpu: 2
              memory: 8Gi
              ephemeral-storage: 4Gi
            limits:
              cpu: 2
              memory: 8Gi
              ephemeral-storage: 4Gi
    listenerTemplate:
      spec:
        securityContext:
          runAsUser: 1001
          runAsGroup: 1001
          fsGroup: 1001
          runAsNonRoot: true
          seccompProfile:
            type: RuntimeDefault
        containers:
        - name: listener
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
              ephemeral-storage: 1Gi
            limits:
              cpu: 100m
              memory: 256Mi
              ephemeral-storage: 1Gi
    EOT
  ]

  depends_on = [helm_release.arc_controller]
}
