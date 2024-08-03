{ pkgs }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python39
    pkgs.ffmpeg
  ];
}
