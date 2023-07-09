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
	"strconv"
	"net"
)

type SSH struct {
	host string
	port int
	key_filename string
	password string
}

func check(e error) {
	if e != nil {
		log.Fatal(e)
	}
}

func readSize(file *os.File) int64 {
	stat, err := file.Stat()
	check(err)
	return stat.Size()
}

func readFile(filename string) []byte {
	file, err := os.Open(filename)
	check(err)
	defer file.Close()
	// Read the file into a byte slice
	bs := make([]byte, readSize(file))
	_, err = bufio.NewReader(file).Read(bs)
	if err != nil && err != io.EOF {
		fmt.Println(err)
	}
	return bs
}

func main() {
	homedir, err := os.UserHomeDir()
	check(err)

	sshdir := filepath.Join(homedir, ".ssh")
	knownhostsfile := filepath.Join(sshdir, "known_hosts")

	user := "art"
	host := "192.168.1.14"
	port := "22"

	hoststring:= net.JoinHostPort(host, port)
	pKeyPath := filepath.Join(sshdir, "id_rsa_legion")
	pKey := readFile(pKeyPath)
	signer, err := ssh.ParsePrivateKey(pKey)
	check(err)

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

