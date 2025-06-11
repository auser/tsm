FROM ubuntu:24.04 

# Configure a SUDO non-root user (no password)
ARG USERNAME=vscode
ARG USER_UID=1001
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo zsh git bash \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME
USER $USERNAME

# Versions
ENV GO_VERSION=1.17

# Go 
ENV GO_DIST=go$GO_VERSION.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Update, install base packages and tools
RUN sudo apt-get update \
    && sudo apt-get -y install git gcc zip unzip apt-transport-https \
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


RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY ./scripts/postCreate.sh /home/$USERNAME/.postCreate.sh

RUN sudo chown $USERNAME:$USERNAME /home/$USERNAME/.zshrc
RUN sudo chmod 644 /home/$USERNAME/.zshrc

RUN sudo chsh -s /bin/zsh $USERNAME