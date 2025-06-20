# Stage 1: Builder
FROM ubuntu:24.04 AS builder

# Configure a SUDO non-root user (no password)
ARG USERNAME=vscode
ARG USER_UID=1001
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update -yq \
    && apt-get install -y sudo zsh git bash make \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

RUN mkdir -p /opt/configs && sudo chown $USERNAME:$USERNAME /opt/configs

USER $USERNAME

# Versions
ENV GO_VERSION=1.17

# Go 
ENV GO_DIST=go$GO_VERSION.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Update, install base packages and tools
RUN sudo apt-get update \
    && sudo apt-get -y install git gcc zip curl unzip apt-transport-https \
    ca-certificates golang-cfssl \
    traceroute net-tools curl dnsutils \
    gnupg-agent \
    software-properties-common \
    gcc-aarch64-linux-gnu \
    #
    # Install go
    && sudo curl -OJ https://dl.google.com/go/$GO_DIST \
    && sudo tar -C /usr/local -xzf $GO_DIST \
    && sudo rm -rf $GO_DIST

# Install Rust and mdBook
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && . $HOME/.cargo/env \
    && cargo install mdbook

RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" && \
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions && \
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting && \
    git clone https://github.com/zsh-users/zsh-history-substring-search.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-history-substring-search && \
    git clone https://github.com/zsh-users/zsh-completions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-completions && \
    sudo chsh -s /bin/zsh $USERNAME

# Install gh
RUN (type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
    && sudo mkdir -p -m 755 /etc/apt/keyrings \
    && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && sudo apt update \
    && sudo apt install gh -y

# Install act
RUN curl -LsSf https://raw.githubusercontent.com/nektos/act/master/install.sh | BINDIR=/usr/local/bin sudo sh

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install rolling-deployer
RUN curl --proto '=https' --tlsv1.2 -LsSf https://github.com/auser/rolling-deployer/releases/download/v0.2.17/rolling-deployer-installer.sh | sh

COPY ./scripts/postCreate.sh /home/$USERNAME/.postCreate.sh

RUN sudo chown $USERNAME:$USERNAME /home/$USERNAME/.zshrc
RUN sudo chmod 644 /home/$USERNAME/.zshrc

RUN sudo chsh -s /bin/zsh $USERNAME

# Stage 2: Final minimal image
FROM ubuntu:24.04 AS final

ARG USERNAME=vscode
ARG USER_UID=1001
ARG USER_GID=$USER_UID

# Install runtime dependencies only
RUN apt-get update -yq \
    && apt-get install -y zsh git curl sudo \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

COPY --from=builder /home/$USERNAME /home/$USERNAME
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/go /usr/local/go
COPY --from=builder /opt/configs /opt/configs
COPY --from=builder /etc/apt/keyrings /etc/apt/keyrings
COPY --from=builder /etc/sudoers.d/$USERNAME /etc/sudoers.d/$USERNAME

USER $USERNAME
ENV PATH=$PATH:/usr/local/go/bin

WORKDIR /home/$USERNAME

# Optionally, re-run chsh in case shell is not set
RUN sudo chsh -s /bin/zsh $USERNAME