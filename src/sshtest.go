package main

import (
	"os"
	"log"
	"golang.org/x/crypto/ssh"
	"golang.org/x/crypto/ssh/knownhosts"
	"path/filepath"
	"bufio"
	"io"
	"fmt"
	_ "strconv"
	"net"
)

type SSH struct {
	host string
	port string `default:"22`
	user string
	password string
	key_filename string
	key_bytes []byte
	knownhostsfile string
}

func (s SSH) setDefaults() {
	if s.knownhostsfile == nil {
		homedir, err := os.UserHomeDir()
		check(err)
		sshdir := filepath.Join(homedir, ".ssh")
		s.knownhostsfile = filepath.Join(sshdir, "known_hosts")
	}
}

func (s SSH) hostString() string {
	return net.JoinHostPort(s.host, s.port)
}

func (s SSH) getKeyBytes() []byte {
	// Read file
	bs, err := os.ReadFile(s.key_filename)
	check(err)

	// Return contents
	return bs
}

func (s SSH) getSigner() (ssh.Signer) {
	signer, err := ssh.ParsePrivateKey(s.getKeyBytes())
	check(err)
	return signer
}

func (s SSH) getConfig() ssh.ClientConfig {
	hostKeyCallback, err := knownhosts.New(s.knownhostsfile)
	check(err)
	conf := &ssh.ClientConfig{
		User: s.user,
		HostKeyCallback: hostKeyCallback,
		Auth: []ssh.AuthMethod{
			ssh.PublicKeys(s.getSigner()),
		},
	}
	return conf
}

func check(e error) {
	if e != nil {
		log.Fatal(e)
	}
}

func main() {
	homedir, err := os.UserHomeDir()
	check(err)

	sshdir := filepath.Join(homedir, ".ssh")
	// knownhostsfile := filepath.Join(sshdir, "known_hosts")

	pKeyPath := filepath.Join(sshdir, "id_rsa_legion")

	s := SSH {
		host: "192.168.1.14",
		user: "art",
		key_filename: pKeyPath,
	}
	s.setDefaults()

	signer, err := s.getSigner()

	hostKeyCallback, err := knownhosts.New(knownhostsfile)
	check(err)

	conf := &ssh.ClientConfig{
		User: user,
		HostKeyCallback: hostKeyCallback,
		Auth: []ssh.AuthMethod{
			ssh.PublicKeys(signer),
		},
	}

	var conn *ssh.Client
	conn, err = ssh.Dial("tcp", hoststring, conf)
	check(err)
	defer conn.Close()

	var session *ssh.Session
	session, err = conn.NewSession()
	check(err)
	defer session.Close()

	var stdin io.WriteCloser
	var stdout, stderr io.Reader

	stdin, err = session.StdinPipe()
	check(err)

	stdout, err = session.StdoutPipe()
	check(err)

	stderr, err = session.StderrPipe()
	check(err)

	wr := make(chan []byte, 10)

	go func() {
		for {
			select {
			case d := <-wr:
				_, err := stdin.Write(d)
				check(err)
			}
		}
	}()

	go func() {
		scanner := bufio.NewScanner(stdout)
		for {
			if tkn := scanner.Scan(); tkn {
				rcv := scanner.Bytes()
				raw := make([]byte, len(rcv))
				copy(raw, rcv)
				fmt.Println(string(raw))
			} else {
				if scanner.Err() != nil {
					fmt.Println(scanner.Err())
				} else {
					fmt.Println("io.EOF")
				}
				return
			}
		}
	}()

	go func() {
		scanner := bufio.NewScanner(stderr)

		for scanner.Scan() {
			fmt.Println(scanner.Text())
		}
	}()

	session.Shell()

	for {
		fmt.Println("$")

		scanner := bufio.NewScanner(os.Stdin)
		scanner.Scan()
		text := scanner.Text()

		wr <- []byte(text + "\n")
	}
}

