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
}

# Runner scale set
resource "helm_release" "arc_runner_set" {
  name             = "arc-runner-set"
  namespace        = kubernetes_namespace.arc_runners.metadata[0].name
  repository       = "oci://ghcr.io/actions/actions-runner-controller-charts"
  chart            = "gha-runner-scale-set"
  version          = "0.12.1"
  create_namespace = false

  set {
    name  = "githubConfigUrl"
    value = "https://github.com/${var.github_repo}"
  }

  set {
    name  = "githubConfigSecret"
    value = kubernetes_secret.arc_github_app.metadata[0].name
  }

  set {
    name  = "runnerScaleSetName"
    value = "gcp-runners"
  }

  set {
    name  = "maxRunners"
    value = "5"
  }

  set {
    name  = "minRunners"
    value = "0"
  }

  depends_on = [helm_release.arc_controller]
}
